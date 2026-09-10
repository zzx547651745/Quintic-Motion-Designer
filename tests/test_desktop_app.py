import unittest

from desktop_app import ALGORITHM_LABELS, WATT_OUTPUT_LABELS, ChineseNavigationToolbar


class DesktopAppLocalizationTests(unittest.TestCase):
    def test_toolbar_labels_and_tips_are_chinese(self) -> None:
        visible_items = [
            item for item in ChineseNavigationToolbar.toolitems if item[0] is not None
        ]
        self.assertEqual(
            [item[0] for item in visible_items],
            ["恢复默认", "后退", "前进", "平移", "框选缩放", "布局设置", "保存图片"],
        )
        self.assertEqual(visible_items[0][3], "home")
        self.assertEqual(visible_items[0][1], "恢复默认视图")

    def test_watt_sixbar_output_labels_are_chinese(self) -> None:
        self.assertEqual(ALGORITHM_LABELS["Watt 六杆机构"], "watt_sixbar")
        self.assertEqual(WATT_OUTPUT_LABELS["G 点 X 分量"], "G_x")
        self.assertEqual(WATT_OUTPUT_LABELS["摇杆角 ψ"], "psi")


if __name__ == "__main__":
    unittest.main()
