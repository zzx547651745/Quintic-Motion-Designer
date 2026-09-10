"""Native Windows GUI for designing piecewise quintic motion charts."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from chart_renderer import export_chart, export_chart_csv, render_chart, safe_filename
from motion_project import (
    ChartConfig,
    MotionProject,
    Waypoint,
    handdrawn_example_project,
)
from watt_sixbar import WattSixBarParameters

ALGORITHM_LABELS = {
    "五次多项式": "quintic",
    "Watt 六杆机构": "watt_sixbar",
}
ALGORITHM_NAMES = {value: key for key, value in ALGORITHM_LABELS.items()}

KIND_LABELS = {
    "位移": "position",
    "速度（对横轴求导）": "velocity",
    "加速度（对横轴二阶求导）": "acceleration",
}
KIND_NAMES = {value: key for key, value in KIND_LABELS.items()}
WATT_PARAMETER_LABELS = (
    ("frame", "AF / L₀"),
    ("ac", "AC / a"),
    ("ab", "AB / b"),
    ("beta_deg", "β (°)"),
    ("cd", "CD / L₂"),
    ("bg", "BG / L₃"),
    ("df", "DF / L₄"),
    ("ge", "GE / L₅"),
    ("fe", "FE / e"),
    ("delta_deg", "δ (°)"),
)
WATT_OUTPUT_LABELS = {
    "B 点 X 分量": "B_x",
    "B 点 Y 分量": "B_y",
    "C 点 X 分量": "C_x",
    "C 点 Y 分量": "C_y",
    "D 点 X 分量": "D_x",
    "D 点 Y 分量": "D_y",
    "E 点 X 分量": "E_x",
    "E 点 Y 分量": "E_y",
    "G 点 X 分量": "G_x",
    "G 点 Y 分量": "G_y",
    "摇杆角 ψ": "psi",
}
WATT_OUTPUT_NAMES = {value: key for key, value in WATT_OUTPUT_LABELS.items()}


class ChineseNavigationToolbar(NavigationToolbar2Tk):
    """Matplotlib toolbar with Chinese tips and a native Chinese layout dialog."""

    toolitems = (
        ("恢复默认", "恢复默认视图", "home", "home"),
        ("后退", "返回上一个视图", "back", "back"),
        ("前进", "前往下一个视图", "forward", "forward"),
        (None, None, None, None),
        ("平移", "拖动鼠标左键平移，拖动右键缩放", "move", "pan"),
        ("框选缩放", "拖动鼠标框选要放大的区域", "zoom_to_rect", "zoom"),
        ("布局设置", "调整图形边距和子图间距", "subplots", "configure_subplots"),
        (None, None, None, None),
        ("保存图片", "将当前预览保存为图片", "filesave", "save_figure"),
    )

    def home(self, *args: object) -> None:
        """Restore the initial axes limits recorded by Matplotlib."""
        super().home(*args)
        self.canvas.draw_idle()

    def configure_subplots(self, *_args: object) -> None:
        existing = getattr(self, "_chinese_subplot_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return

        dialog = tk.Toplevel(self.winfo_toplevel())
        self._chinese_subplot_dialog = dialog
        dialog.title("子图布局设置")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())

        subplot = self.canvas.figure.subplotpars
        initial = {
            "left": subplot.left,
            "bottom": subplot.bottom,
            "right": subplot.right,
            "top": subplot.top,
            "wspace": subplot.wspace,
            "hspace": subplot.hspace,
        }
        labels = {
            "left": "左边距",
            "bottom": "底边距",
            "right": "右边距",
            "top": "顶边距",
            "wspace": "子图横向间距",
            "hspace": "子图纵向间距",
        }
        variables = {name: tk.DoubleVar(value=value) for name, value in initial.items()}
        value_labels: dict[str, ttk.Label] = {}

        def apply_layout(_value: str | None = None) -> None:
            values = {name: variable.get() for name, variable in variables.items()}
            if values["left"] >= values["right"] or values["bottom"] >= values["top"]:
                return
            self.canvas.figure.subplots_adjust(**values)
            for name, label in value_labels.items():
                label.configure(text=f"{values[name]:.3f}")
            self.canvas.draw_idle()

        content = ttk.Frame(dialog, padding=14)
        content.pack(fill=tk.BOTH, expand=True)
        for row, name in enumerate(labels):
            ttk.Label(content, text=labels[name], width=14).grid(
                row=row, column=0, sticky=tk.W, pady=5
            )
            scale = ttk.Scale(
                content,
                from_=0.0,
                to=1.0,
                variable=variables[name],
                command=apply_layout,
                length=360,
            )
            scale.grid(row=row, column=1, padx=8, pady=5)
            value_label = ttk.Label(content, text=f"{initial[name]:.3f}", width=7)
            value_label.grid(row=row, column=2, sticky=tk.E)
            value_labels[name] = value_label

        def restore_defaults() -> None:
            for name, value in initial.items():
                variables[name].set(value)
            apply_layout()

        actions = ttk.Frame(content)
        actions.grid(row=len(labels), column=0, columnspan=3, sticky=tk.E, pady=(12, 0))
        ttk.Button(actions, text="恢复默认", command=restore_defaults).pack(
            side=tk.LEFT
        )
        ttk.Button(actions, text="关闭", command=dialog.destroy).pack(
            side=tk.LEFT, padx=(8, 0)
        )

    def save_figure(self, *_args: object) -> None:
        filename = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="保存当前预览",
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg"),
                ("SVG 矢量图", "*.svg"),
                ("PDF 文档", "*.pdf"),
            ],
        )
        if filename:
            try:
                self.canvas.figure.savefig(filename, dpi=180, bbox_inches="tight")
            except Exception as exc:
                messagebox.showerror("保存失败", str(exc), parent=self.winfo_toplevel())


class MotionDesignerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("运动曲线设计器")
        self.root.geometry("1420x860")
        self.root.minsize(1120, 700)

        self.project = handdrawn_example_project()
        self.project_path: Path | None = None
        self.current_index = 0
        self._loading_form = False
        self._preview_job: str | None = None

        self._configure_style()
        self._create_variables()
        self._create_menu()
        self._create_layout()
        self._bind_variable_updates()
        self._reload_chart_list(select=0)
        self._update_window_title()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TButton", padding=(8, 5))

    def _create_variables(self) -> None:
        self.name_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.x_label_var = tk.StringVar()
        self.y_label_var = tk.StringVar()
        self.algorithm_var = tk.StringVar()
        self.kind_var = tk.StringVar()
        self.original_var = tk.BooleanVar(value=True)
        self.grid_var = tk.BooleanVar(value=True)
        self.point_x_var = tk.StringVar()
        self.point_y_var = tk.StringVar()
        defaults = WattSixBarParameters()
        self.watt_parameter_vars = {
            name: tk.StringVar(value=f"{getattr(defaults, name):g}")
            for name, _label in WATT_PARAMETER_LABELS
        }
        self.watt_branch_d_var = tk.StringVar(value="+1")
        self.watt_branch_g_var = tk.StringVar(value="+1")
        self.watt_start_var = tk.StringVar(value="0")
        self.watt_end_var = tk.StringVar(value="360")
        self.watt_samples_var = tk.StringVar(value="361")
        self.watt_omega_var = tk.StringVar(value="1")
        self.watt_alpha_var = tk.StringVar(value="0")
        self.watt_output_var = tk.StringVar(value="G 点 X 分量")
        self.status_var = tk.StringVar(value="就绪")

    def _create_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(
            label="新建项目", command=self.new_project, accelerator="Ctrl+N"
        )
        file_menu.add_command(
            label="打开项目…", command=self.open_project, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="保存项目", command=self.save_project, accelerator="Ctrl+S"
        )
        file_menu.add_command(label="项目另存为…", command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="导出当前图片…", command=self.export_current)
        file_menu.add_command(label="批量导出 PNG…", command=self.export_all)
        file_menu.add_separator()
        file_menu.add_command(
            label="导出当前图数据 CSV…", command=self.export_current_data
        )
        file_menu.add_command(
            label="批量导出全部数据 CSV…", command=self.export_all_data
        )
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.destroy)
        menu.add_cascade(label="文件", menu=file_menu)
        self.root.config(menu=menu)
        self.root.bind("<Control-n>", lambda _event: self.new_project())
        self.root.bind("<Control-o>", lambda _event: self.open_project())
        self.root.bind("<Control-s>", lambda _event: self.save_project())

    def _create_layout(self) -> None:
        outer = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        editor = ttk.Frame(outer, padding=6)
        preview = ttk.Frame(outer, padding=6)
        outer.add(editor, weight=0)
        outer.add(preview, weight=1)
        self._create_editor(editor)
        self._create_preview(preview)

        status = ttk.Label(
            self.root, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN
        )
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _create_editor(self, parent: ttk.Frame) -> None:
        parent.configure(width=440)
        ttk.Label(parent, text="图列表", style="Section.TLabel").pack(anchor=tk.W)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.X, pady=(5, 6))
        self.chart_list = tk.Listbox(
            list_frame,
            height=6,
            exportselection=False,
            font=("Microsoft YaHei UI", 10),
        )
        self.chart_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, command=self.chart_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chart_list.configure(yscrollcommand=scrollbar.set)
        self.chart_list.bind("<<ListboxSelect>>", self._on_chart_selected)

        chart_buttons = ttk.Frame(parent)
        chart_buttons.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(chart_buttons, text="添加图", command=self.add_chart).pack(
            side=tk.LEFT
        )
        ttk.Button(chart_buttons, text="复制图", command=self.duplicate_chart).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(chart_buttons, text="删除图", command=self.delete_chart).pack(
            side=tk.LEFT
        )

        properties = ttk.LabelFrame(parent, text="图属性", padding=8)
        properties.pack(fill=tk.X, pady=(0, 10))
        self._labeled_entry(properties, "列表名称", self.name_var, 0)
        self._labeled_entry(properties, "图标题", self.title_var, 1)
        self._labeled_entry(properties, "横轴文字", self.x_label_var, 2)
        self._labeled_entry(properties, "纵轴文字", self.y_label_var, 3)

        ttk.Label(properties, text="算法").grid(row=4, column=0, sticky=tk.W, pady=4)
        algorithm_box = ttk.Combobox(
            properties,
            textvariable=self.algorithm_var,
            values=list(ALGORITHM_LABELS),
            state="readonly",
            width=27,
        )
        algorithm_box.grid(row=4, column=1, sticky=tk.EW, padx=(8, 0), pady=4)
        ttk.Label(properties, text="曲线类型").grid(
            row=5, column=0, sticky=tk.W, pady=4
        )
        kind_box = ttk.Combobox(
            properties,
            textvariable=self.kind_var,
            values=list(KIND_LABELS),
            state="readonly",
            width=27,
        )
        kind_box.grid(row=5, column=1, sticky=tk.EW, padx=(8, 0), pady=4)
        properties.columnconfigure(1, weight=1)
        self.original_check = ttk.Checkbutton(
            properties, text="位移图显示原始折线", variable=self.original_var
        )
        self.original_check.grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(5, 0)
        )
        ttk.Checkbutton(properties, text="显示网格", variable=self.grid_var).grid(
            row=7, column=0, columnspan=2, sticky=tk.W
        )

        parameter_area = ttk.Frame(parent)
        parameter_area.pack(fill=tk.BOTH, expand=True)
        parameter_area.rowconfigure(0, weight=1)
        parameter_area.columnconfigure(0, weight=1)
        points = ttk.LabelFrame(
            parameter_area, text="拐点（横轴值必须递增）", padding=8
        )
        points.grid(row=0, column=0, sticky=tk.NSEW)
        self.points_frame = points
        self.point_tree = ttk.Treeview(
            points,
            columns=("x", "y"),
            show="headings",
            height=9,
            selectmode="browse",
        )
        self.point_tree.heading("x", text="横轴值")
        self.point_tree.heading("y", text="纵轴值")
        self.point_tree.column("x", width=120, anchor=tk.CENTER)
        self.point_tree.column("y", width=120, anchor=tk.CENTER)
        self.point_tree.pack(fill=tk.BOTH, expand=True)
        self.point_tree.bind("<<TreeviewSelect>>", self._on_point_selected)

        point_form = ttk.Frame(points)
        point_form.pack(fill=tk.X, pady=(7, 3))
        ttk.Label(point_form, text="X").grid(row=0, column=0)
        ttk.Entry(point_form, textvariable=self.point_x_var, width=12).grid(
            row=0, column=1, padx=(3, 10)
        )
        ttk.Label(point_form, text="Y").grid(row=0, column=2)
        ttk.Entry(point_form, textvariable=self.point_y_var, width=12).grid(
            row=0, column=3, padx=(3, 0)
        )
        point_actions = ttk.Frame(points)
        point_actions.pack(fill=tk.X)
        ttk.Button(point_actions, text="添加拐点", command=self.add_point).pack(
            side=tk.LEFT
        )
        ttk.Button(point_actions, text="更新选中", command=self.update_point).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(point_actions, text="删除选中", command=self.delete_point).pack(
            side=tk.LEFT
        )
        self._create_watt_editor(parameter_area)

    def _create_watt_editor(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Watt 六杆机构参数", padding=8)
        frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.watt_frame = frame
        for index, (name, label) in enumerate(WATT_PARAMETER_LABELS):
            row = index // 2
            column = (index % 2) * 2
            ttk.Label(frame, text=label).grid(
                row=row, column=column, sticky=tk.W, padx=(0, 4), pady=3
            )
            ttk.Entry(
                frame, textvariable=self.watt_parameter_vars[name], width=11
            ).grid(row=row, column=column + 1, sticky=tk.EW, padx=(0, 10), pady=3)

        controls = (
            ("D 装配分支", self.watt_branch_d_var, ("+1", "-1")),
            ("G 装配分支", self.watt_branch_g_var, ("+1", "-1")),
            ("起始角 (°)", self.watt_start_var, None),
            ("终止角 (°)", self.watt_end_var, None),
            ("采样点数", self.watt_samples_var, None),
            ("预览输出", self.watt_output_var, tuple(WATT_OUTPUT_LABELS)),
            ("角速度 (rad/s)", self.watt_omega_var, None),
            ("角加速度 (rad/s²)", self.watt_alpha_var, None),
        )
        start_row = (len(WATT_PARAMETER_LABELS) + 1) // 2
        for index, (label, variable, values) in enumerate(controls):
            row = start_row + index // 2
            column = (index % 2) * 2
            ttk.Label(frame, text=label).grid(
                row=row, column=column, sticky=tk.W, padx=(0, 4), pady=3
            )
            if values is None:
                widget: ttk.Widget = ttk.Entry(frame, textvariable=variable, width=11)
            else:
                widget = ttk.Combobox(
                    frame,
                    textvariable=variable,
                    values=values,
                    state="readonly",
                    width=10,
                )
            widget.grid(row=row, column=column + 1, sticky=tk.EW, padx=(0, 10), pady=3)
        action_row = start_row + (len(controls) + 1) // 2
        ttk.Button(frame, text="应用参数并刷新", command=self.refresh_preview).grid(
            row=action_row, column=0, columnspan=4, sticky=tk.EW, pady=(8, 3)
        )
        ttk.Label(
            frame,
            text="固定 A=(0,0)，F=(AF,0)；杆长单位为 mm。",
            foreground="#475569",
        ).grid(row=action_row + 1, column=0, columnspan=4, sticky=tk.W, pady=(4, 0))
        for column in (1, 3):
            frame.columnconfigure(column, weight=1)

    @staticmethod
    def _labeled_entry(
        parent: ttk.Widget, label: str, variable: tk.StringVar, row: int
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        ttk.Entry(parent, textvariable=variable, width=29).grid(
            row=row, column=1, sticky=tk.EW, padx=(8, 0), pady=4
        )

    def _create_preview(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(header, text="预览", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="刷新预览", command=self.refresh_preview).pack(
            side=tk.RIGHT
        )
        ttk.Button(header, text="导出当前图", command=self.export_current).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(header, text="批量导出 PNG", command=self.export_all).pack(
            side=tk.RIGHT
        )
        ttk.Button(header, text="导出数据 CSV", command=self.export_current_data).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(header, text="批量数据 CSV", command=self.export_all_data).pack(
            side=tk.RIGHT
        )
        self.figure = Figure(figsize=(9, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = ChineseNavigationToolbar(
            self.canvas, toolbar_frame, pack_toolbar=False
        )
        self.toolbar.update()
        self.toolbar.pack(side=tk.LEFT, fill=tk.X)

    def _bind_variable_updates(self) -> None:
        variables = (
            self.name_var,
            self.title_var,
            self.x_label_var,
            self.y_label_var,
            self.algorithm_var,
            self.kind_var,
            self.original_var,
            self.grid_var,
        )
        for variable in variables:
            variable.trace_add("write", self._schedule_metadata_update)

    @property
    def current_chart(self) -> ChartConfig:
        return self.project.charts[self.current_index]

    def _schedule_metadata_update(self, *_args: object) -> None:
        if self._loading_form:
            return
        self._update_algorithm_panel()
        try:
            self._sync_metadata()
        except ValueError as exc:
            self.status_var.set(f"参数尚未生效：{exc}")
            return
        if self._preview_job is not None:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(300, self.refresh_preview)

    def _sync_metadata(self) -> None:
        chart = self.current_chart
        chart.name = self.name_var.get().strip() or "未命名图"
        chart.title = self.title_var.get()
        chart.x_label = self.x_label_var.get()
        chart.y_label = self.y_label_var.get()
        chart.algorithm = ALGORITHM_LABELS.get(self.algorithm_var.get(), "quintic")
        chart.curve_kind = KIND_LABELS.get(self.kind_var.get(), "position")
        chart.show_original = self.original_var.get()
        chart.show_grid = self.grid_var.get()
        if chart.algorithm == "watt_sixbar":
            chart.watt_parameters = WattSixBarParameters(
                **{
                    name: float(variable.get())
                    for name, variable in self.watt_parameter_vars.items()
                },
                branch_d=int(self.watt_branch_d_var.get()),
                branch_g=int(self.watt_branch_g_var.get()),
            )
            chart.watt_output = WATT_OUTPUT_LABELS.get(
                self.watt_output_var.get(), "G_x"
            )
            chart.watt_start_deg = float(self.watt_start_var.get())
            chart.watt_end_deg = float(self.watt_end_var.get())
            chart.watt_samples = int(self.watt_samples_var.get())
            chart.watt_omega = float(self.watt_omega_var.get())
            chart.watt_alpha = float(self.watt_alpha_var.get())
            chart.validate()
        if self.chart_list.size() > self.current_index:
            self.chart_list.delete(self.current_index)
            self.chart_list.insert(self.current_index, chart.name)
            self.chart_list.selection_set(self.current_index)
        self._mark_changed()

    def _load_chart_form(self) -> None:
        chart = self.current_chart
        self._loading_form = True
        try:
            self.name_var.set(chart.name)
            self.title_var.set(chart.title)
            self.x_label_var.set(chart.x_label)
            self.y_label_var.set(chart.y_label)
            self.algorithm_var.set(ALGORITHM_NAMES[chart.algorithm])
            self.kind_var.set(KIND_NAMES[chart.curve_kind])
            self.original_var.set(chart.show_original)
            self.grid_var.set(chart.show_grid)
            for name, _label in WATT_PARAMETER_LABELS:
                self.watt_parameter_vars[name].set(
                    f"{getattr(chart.watt_parameters, name):g}"
                )
            self.watt_branch_d_var.set(f"{chart.watt_parameters.branch_d:+d}")
            self.watt_branch_g_var.set(f"{chart.watt_parameters.branch_g:+d}")
            self.watt_start_var.set(f"{chart.watt_start_deg:g}")
            self.watt_end_var.set(f"{chart.watt_end_deg:g}")
            self.watt_samples_var.set(str(chart.watt_samples))
            self.watt_omega_var.set(f"{chart.watt_omega:g}")
            self.watt_alpha_var.set(f"{chart.watt_alpha:g}")
            self.watt_output_var.set(WATT_OUTPUT_NAMES[chart.watt_output])
            self._reload_points()
            self._update_algorithm_panel()
        finally:
            self._loading_form = False
        self.refresh_preview()

    def _update_algorithm_panel(self) -> None:
        if ALGORITHM_LABELS.get(self.algorithm_var.get()) == "watt_sixbar":
            self.watt_frame.tkraise()
            self.original_check.state(["disabled"])
        else:
            self.points_frame.tkraise()
            self.original_check.state(["!disabled"])

    def _reload_chart_list(self, select: int) -> None:
        self.chart_list.delete(0, tk.END)
        for chart in self.project.charts:
            self.chart_list.insert(tk.END, chart.name)
        self.current_index = min(select, len(self.project.charts) - 1)
        self.chart_list.selection_set(self.current_index)
        self.chart_list.activate(self.current_index)
        self._load_chart_form()

    def _reload_points(self) -> None:
        for item in self.point_tree.get_children():
            self.point_tree.delete(item)
        for index, point in enumerate(self.current_chart.points):
            self.point_tree.insert(
                "",
                tk.END,
                iid=str(index),
                values=(f"{point.input_value:g}", f"{point.output_value:g}"),
            )

    def _on_chart_selected(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.chart_list.curselection()
        if not selection or selection[0] == self.current_index:
            return
        self.current_index = selection[0]
        self._load_chart_form()

    def _on_point_selected(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.point_tree.selection()
        if not selection:
            return
        point = self.current_chart.points[int(selection[0])]
        self.point_x_var.set(f"{point.input_value:g}")
        self.point_y_var.set(f"{point.output_value:g}")

    def _parse_point(self) -> Waypoint | None:
        try:
            return Waypoint(
                float(self.point_x_var.get()), float(self.point_y_var.get())
            )
        except ValueError:
            messagebox.showerror("输入错误", "横轴值和纵轴值必须是有效数字。")
            return None

    def add_point(self) -> None:
        point = self._parse_point()
        if point is None:
            return
        if any(
            existing.input_value == point.input_value
            for existing in self.current_chart.points
        ):
            messagebox.showerror("输入错误", "横轴值不能重复。")
            return
        self.current_chart.points.append(point)
        self.current_chart.sort_points()
        self._after_point_change("已添加拐点")

    def update_point(self) -> None:
        selection = self.point_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选中要更新的拐点。")
            return
        point = self._parse_point()
        if point is None:
            return
        old_index = int(selection[0])
        if any(
            index != old_index and existing.input_value == point.input_value
            for index, existing in enumerate(self.current_chart.points)
        ):
            messagebox.showerror("输入错误", "横轴值不能重复。")
            return
        self.current_chart.points[old_index] = point
        self.current_chart.sort_points()
        self._after_point_change("已更新拐点")

    def delete_point(self) -> None:
        selection = self.point_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选中要删除的拐点。")
            return
        if len(self.current_chart.points) <= 2:
            messagebox.showwarning("无法删除", "每张图至少需要两个拐点。")
            return
        del self.current_chart.points[int(selection[0])]
        self._after_point_change("已删除拐点")

    def _after_point_change(self, status: str) -> None:
        self.point_x_var.set("")
        self.point_y_var.set("")
        self._reload_points()
        self._mark_changed()
        self.status_var.set(status)
        self.refresh_preview()

    def add_chart(self) -> None:
        self.project.charts.append(
            ChartConfig(name=f"新图 {len(self.project.charts) + 1}")
        )
        self._mark_changed()
        self._reload_chart_list(len(self.project.charts) - 1)

    def duplicate_chart(self) -> None:
        self.project.charts.insert(
            self.current_index + 1, self.current_chart.duplicate()
        )
        self._mark_changed()
        self._reload_chart_list(self.current_index + 1)

    def delete_chart(self) -> None:
        if len(self.project.charts) <= 1:
            messagebox.showwarning("无法删除", "项目至少需要保留一张图。")
            return
        name = self.current_chart.name
        if not messagebox.askyesno("确认删除", f"确定删除“{name}”吗？"):
            return
        del self.project.charts[self.current_index]
        self._mark_changed()
        self._reload_chart_list(max(0, self.current_index - 1))

    def refresh_preview(self) -> None:
        self._preview_job = None
        try:
            self._sync_metadata()
            render_chart(self.current_chart, self.figure)
            self.canvas.draw_idle()
            if self.current_chart.algorithm == "watt_sixbar":
                parameters = self.current_chart.watt_parameters
                grashof = "满足" if parameters.grashof_satisfied else "不满足"
                self.status_var.set(
                    f"正在预览：{self.current_chart.name}（Watt 六杆，"
                    f"Grashof {grashof}）"
                )
            else:
                point_count = len(self.current_chart.points)
                self.status_var.set(
                    f"正在预览：{self.current_chart.name}（{point_count} 个拐点）"
                )
        except (
            Exception
        ) as exc:  # GUI boundary: show validation failures without crashing.
            self.status_var.set(f"无法预览：{exc}")

    def new_project(self) -> None:
        if not messagebox.askyesno(
            "新建项目", "确定新建项目吗？当前未保存内容将被清空。"
        ):
            return
        self.project = MotionProject()
        self.project_path = None
        self._reload_chart_list(0)
        self._update_window_title()

    def open_project(self) -> None:
        filename = filedialog.askopenfilename(
            title="打开运动曲线项目",
            filetypes=[("运动曲线项目", "*.qmp.json"), ("JSON 文件", "*.json")],
        )
        if not filename:
            return
        try:
            self.project = MotionProject.load(filename)
            self.project_path = Path(filename)
            self._reload_chart_list(0)
            self._update_window_title()
            self.status_var.set(f"已打开：{filename}")
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def save_project(self) -> None:
        if self.project_path is None:
            self.save_project_as()
            return
        self._save_to(self.project_path)

    def save_project_as(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="保存运动曲线项目",
            defaultextension=".qmp.json",
            filetypes=[("运动曲线项目", "*.qmp.json"), ("JSON 文件", "*.json")],
        )
        if filename:
            self.project_path = Path(filename)
            self.project.name = self.project_path.name.removesuffix(".qmp.json")
            self._save_to(self.project_path)

    def _save_to(self, path: Path) -> None:
        try:
            self._sync_metadata()
            self.project.save(path)
            self.status_var.set(f"项目已保存：{path}")
            self._update_window_title()
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def export_current(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="导出当前图片",
            initialfile=f"{safe_filename(self.current_chart.name)}.png",
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg"),
                ("SVG 矢量图", "*.svg"),
                ("PDF 文档", "*.pdf"),
            ],
        )
        if not filename:
            return
        try:
            self._sync_metadata()
            export_chart(self.current_chart, filename)
            self.status_var.set(f"图片已导出：{filename}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def export_all(self) -> None:
        folder = filedialog.askdirectory(title="选择批量导出目录")
        if not folder:
            return
        try:
            self._sync_metadata()
            used: set[str] = set()
            for index, chart in enumerate(self.project.charts, start=1):
                base = safe_filename(chart.name, f"motion_chart_{index}")
                filename = base
                suffix = 2
                while filename.casefold() in used:
                    filename = f"{base}_{suffix}"
                    suffix += 1
                used.add(filename.casefold())
                export_chart(chart, Path(folder) / f"{filename}.png")
            self.status_var.set(
                f"已批量导出 {len(self.project.charts)} 张 PNG：{folder}"
            )
            messagebox.showinfo(
                "导出完成", f"已导出 {len(self.project.charts)} 张图片。"
            )
        except Exception as exc:
            messagebox.showerror("批量导出失败", str(exc))

    def export_current_data(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="导出当前图数据",
            initialfile=f"{safe_filename(self.current_chart.name)}_数据.csv",
            defaultextension=".csv",
            filetypes=[("CSV 数据文件", "*.csv")],
        )
        if not filename:
            return
        try:
            self._sync_metadata()
            export_chart_csv(self.current_chart, filename)
            self.status_var.set(f"当前图数据已导出：{filename}")
        except Exception as exc:
            messagebox.showerror("数据导出失败", str(exc))

    def export_all_data(self) -> None:
        folder = filedialog.askdirectory(title="选择批量数据导出目录")
        if not folder:
            return
        try:
            self._sync_metadata()
            used: set[str] = set()
            for index, chart in enumerate(self.project.charts, start=1):
                base = safe_filename(chart.name, f"motion_chart_{index}")
                filename = base
                suffix = 2
                while filename.casefold() in used:
                    filename = f"{base}_{suffix}"
                    suffix += 1
                used.add(filename.casefold())
                export_chart_csv(chart, Path(folder) / f"{filename}_数据.csv")
            self.status_var.set(
                f"已批量导出 {len(self.project.charts)} 个 CSV：{folder}"
            )
            messagebox.showinfo(
                "数据导出完成",
                f"已按图导出 {len(self.project.charts)} 个 CSV，"
                "每个文件均包含横轴值、位移、速度和加速度。",
            )
        except Exception as exc:
            messagebox.showerror("批量数据导出失败", str(exc))

    def _mark_changed(self) -> None:
        self._update_window_title(changed=True)

    def _update_window_title(self, changed: bool = False) -> None:
        project_name = (
            self.project_path.name if self.project_path else self.project.name
        )
        marker = " *" if changed else ""
        self.root.title(f"{project_name}{marker} - 运动曲线设计器")


def main() -> None:
    root = tk.Tk()
    MotionDesignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
