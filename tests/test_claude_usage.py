from __future__ import annotations

import importlib.util
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path
import sys
import unittest


SCRIPT_PATH = Path(__file__).parent.parent / "python" / "claude-usage"


def load_module():
    loader = SourceFileLoader("ccusage_month_graph", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("ccusage_month_graph", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


class TestCcusageMonthGraph(unittest.TestCase):
    def test_build_ccusage_commands_always_use_npx(self):
        module = load_module()

        commands = module.build_ccusage_commands(
            since=date(2026, 4, 1),
            until=date(2026, 4, 11),
            locale=None,
            mode="auto",
            project=None,
            offline=True,
        )

        self.assertEqual(
            commands,
            [
                [
                    "npx",
                    "-y",
                    "ccusage",
                    "daily",
                    "--json",
                    "--instances",
                    "--since",
                    "20260401",
                    "--until",
                    "20260411",
                    "--mode",
                    "auto",
                    "--order",
                    "asc",
                    "--offline",
                ]
            ],
        )

    def test_build_daily_points_aggregates_projects_and_fills_month(self):
        module = load_module()

        payload = {
            "projects": {
                "-Users-dan-src-one": [
                    {"date": "2026-04-01", "totalCost": 1.25},
                    {"date": "2026-04-03", "totalCost": 2.00},
                ],
                "-Users-dan-src-two": [
                    {"date": "2026-04-01", "totalCost": 0.75},
                ],
            }
        }

        points = module.build_daily_points(
            payload,
            "totalCost",
            date(2026, 4, 1),
            date(2026, 4, 4),
            date(2026, 4, 2),
        )

        self.assertEqual([point.day.isoformat() for point in points], [
            "2026-04-01",
            "2026-04-02",
            "2026-04-03",
            "2026-04-04",
        ])
        self.assertEqual([str(point.value) for point in points], ["2.00", "0", "0", "0"])
        self.assertEqual([str(point.cumulative) for point in points], ["2.00", "2.00", "0", "0"])
        self.assertEqual(
            [project.project for project in points[0].projects],
            ["/Users-dan-src-one", "/Users-dan-src-two"],
        )

    def test_build_chart_model_includes_projection_and_future_nulls(self):
        module = load_module()

        points = [
            module.DailyPoint(
                day=date(2026, 4, 1),
                value=module.Decimal("2"),
                cumulative=module.Decimal("2"),
                projects=[module.ProjectBreakdown(project="/one", value=module.Decimal("2"))],
            ),
            module.DailyPoint(
                day=date(2026, 4, 2),
                value=module.Decimal("3"),
                cumulative=module.Decimal("5"),
                projects=[module.ProjectBreakdown(project="/two", value=module.Decimal("3"))],
            ),
            module.DailyPoint(
                day=date(2026, 4, 3),
                value=module.Decimal("0"),
                cumulative=module.Decimal("0"),
                projects=[],
            ),
        ]

        model = module.build_chart_model(
            points,
            "totalCost",
            "2026-04",
            date(2026, 4, 2),
        )

        self.assertEqual(model["todayDay"], 2)
        self.assertEqual(model["totalLabel"], "$5.00")
        self.assertEqual(model["predictionEndLabel"], "$7.50")
        self.assertEqual(model["targetEndLabel"], "$1,000.00")
        self.assertEqual(model["daily"][2]["cumulative"], None)
        self.assertEqual(model["prediction"], [2.5, 5.0, 7.5])
        self.assertEqual(model["target"], [333.3333, 666.6667, 1000.0])

    def test_render_html_contains_embedded_model(self):
        module = load_module()

        html = module.render_html(
            {
                "month": "2026-04",
                "metric": "totalCost",
                "metricLabel": "Cumulative cost",
                "daysInMonth": 3,
                "todayDay": 2,
                "totalLabel": "$5.00",
                "predictionEndLabel": "$7.50",
                "targetEndLabel": "$1,000.00",
                "yMax": 10.0,
                "daily": [],
                "prediction": [2.5, 5.0, 7.5],
                "target": [333.3333, 666.6667, 1000.0],
            }
        )

        self.assertIn("Claude Code usage for 2026-04", html)
        self.assertNotIn("system default", html)
        self.assertIn('"prediction":[2.5,5.0,7.5]', html)
        self.assertIn('"target":[333.3333,666.6667,1000.0]', html)
        self.assertNotIn("prediction-line", html)
        self.assertIn('class: "target-line"', html)
        self.assertIn('"$1000"', html)


if __name__ == "__main__":
    unittest.main()
