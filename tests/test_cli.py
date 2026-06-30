import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

from morning_report.cli import build_report, load_active_projects


class MorningReportTests(unittest.TestCase):
    def test_load_active_projects_filters_paused_projects(self) -> None:
        payload = {
            "projects": [
                {"name": "Active", "status": "active"},
                {"name": "Implicit Active"},
                {"name": "Paused", "status": "paused"},
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "projects.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            projects = load_active_projects(path)

        self.assertEqual([project["name"] for project in projects], ["Active", "Implicit Active"])

    def test_build_report_uses_chinese_project_sections(self) -> None:
        projects = [
            {
                "name": "Morning Report",
                "goal": "自动生成早报",
                "progress": ["完成配置读取", "完成报告生成"],
                "next": "发送到 Discord",
                "blockers": [],
            }
        ]

        report = build_report(projects, dt.datetime(2026, 6, 30, 8, 0))

        self.assertIn("今天是 2026-06-30", report)
        self.assertIn("1. Morning Report", report)
        self.assertIn("目标：自动生成早报", report)
        self.assertIn("进展：完成配置读取；完成报告生成", report)
        self.assertIn("下一步：发送到 Discord", report)

    def test_build_report_handles_empty_active_projects(self) -> None:
        report = build_report([], dt.datetime(2026, 6, 30, 8, 0))

        self.assertIn("目前没有标记为 active 的项目。", report)


if __name__ == "__main__":
    unittest.main()
