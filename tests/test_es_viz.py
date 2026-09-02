from __future__ import annotations

import importlib.util
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).parent.parent / "python" / "es-viz"


def load_module():
    loader = SourceFileLoader("es_viz", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("es_viz", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


es_viz = load_module()


def kinds(columns):
    return [(c.name, c.kind) for c in columns]


class TestFlattenAggregations(unittest.TestCase):
    def test_date_histogram_yields_one_time_dimension(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by5m": {
                    "buckets": [
                        {
                            "key_as_string": "2026-08-31T18:00:00.000Z",
                            "key": 1788199200000,
                            "doc_count": 25173,
                        },
                        {
                            "key_as_string": "2026-08-31T18:05:00.000Z",
                            "key": 1788199500000,
                            "doc_count": 22539,
                        },
                    ]
                }
            }
        )

        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertEqual(table.name, "by5m")
        self.assertEqual(kinds(table.dims), [("by5m", "time")])
        self.assertEqual(kinds(table.measures), [("doc_count", "number")])
        self.assertEqual(
            table.rows,
            [
                {"by5m": "2026-08-31T18:00:00.000Z", "doc_count": 25173},
                {"by5m": "2026-08-31T18:05:00.000Z", "doc_count": 22539},
            ],
        )

    def test_terms_on_keyword_field_is_a_category_dimension(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by_ns": {
                    "buckets": [
                        {"key": "0cf57c40", "doc_count": 7},
                        {"key": "1ab99e21", "doc_count": 3},
                    ]
                }
            }
        )

        self.assertEqual(kinds(tables[0].dims), [("by_ns", "category")])

    def test_histogram_on_numeric_field_is_a_number_dimension(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by_size": {
                    "buckets": [
                        {"key": 0.0, "key_as_string": "0.0", "doc_count": 4},
                        {"key": 100.0, "key_as_string": "100.0", "doc_count": 9},
                    ]
                }
            }
        )

        self.assertEqual(kinds(tables[0].dims), [("by_size", "number")])

    def test_nested_aggs_give_one_dimension_per_level(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by5m": {
                    "buckets": [
                        {
                            "key_as_string": "2026-08-31T18:00:00.000Z",
                            "key": 1788199200000,
                            "doc_count": 30,
                            "by_status": {
                                "buckets": [
                                    {"key": "Running", "doc_count": 20},
                                    {"key": "Completed", "doc_count": 10},
                                ]
                            },
                        }
                    ]
                }
            }
        )

        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertEqual(table.name, "by5m / by_status")
        self.assertEqual(kinds(table.dims), [("by5m", "time"), ("by_status", "category")])
        self.assertEqual(
            table.rows,
            [
                {
                    "by5m": "2026-08-31T18:00:00.000Z",
                    "by_status": "Running",
                    "doc_count": 20,
                },
                {
                    "by5m": "2026-08-31T18:00:00.000Z",
                    "by_status": "Completed",
                    "doc_count": 10,
                },
            ],
        )

    def test_keyed_buckets_map_is_normalized(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by_state": {
                    "buckets": {
                        "open": {"doc_count": 5},
                        "closed": {"doc_count": 2},
                    }
                }
            }
        )

        self.assertEqual(kinds(tables[0].dims), [("by_state", "category")])
        self.assertEqual(
            tables[0].rows,
            [{"by_state": "open", "doc_count": 5}, {"by_state": "closed", "doc_count": 2}],
        )

    def test_metric_aggs_become_measures(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by_ns": {
                    "buckets": [
                        {
                            "key": "ns-a",
                            "doc_count": 12,
                            "avg_len": {"value": 4.5},
                            "len_stats": {"count": 12, "min": 1.0, "max": 9.0},
                        }
                    ]
                }
            }
        )

        table = tables[0]
        self.assertEqual(
            kinds(table.measures),
            [
                ("doc_count", "number"),
                ("avg_len", "number"),
                ("len_stats.count", "number"),
                ("len_stats.min", "number"),
                ("len_stats.max", "number"),
            ],
        )
        self.assertEqual(
            table.rows,
            [
                {
                    "by_ns": "ns-a",
                    "doc_count": 12,
                    "avg_len": 4.5,
                    "len_stats.count": 12,
                    "len_stats.min": 1.0,
                    "len_stats.max": 9.0,
                }
            ],
        )

    def test_top_level_metric_aggs_give_a_dimensionless_table(self):
        tables = es_viz.tables_from_aggregations({"total": {"value": 91}})

        self.assertEqual(tables[0].dims, [])
        self.assertEqual(tables[0].rows, [{"total": 91}])

    def test_sibling_bucket_aggs_give_separate_tables(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by_ns": {"buckets": [{"key": "ns-a", "doc_count": 1}]},
                "by_status": {"buckets": [{"key": "Running", "doc_count": 2}]},
            }
        )

        self.assertEqual([t.name for t in tables], ["by_ns", "by_status"])

    def test_top_hits_agg_is_not_flattened_into_measures(self):
        tables = es_viz.tables_from_aggregations(
            {
                "by_ns": {
                    "buckets": [
                        {
                            "key": "ns-a",
                            "doc_count": 1,
                            "newest": {"hits": {"total": {"value": 1}, "hits": []}},
                        }
                    ]
                }
            }
        )

        self.assertEqual(kinds(tables[0].measures), [("doc_count", "number")])


class TestNonAggregationResponses(unittest.TestCase):
    def test_hits_are_flattened_into_a_table(self):
        table = es_viz.table_from_hits(
            [
                {
                    "_id": "abc",
                    "_source": {
                        "WorkflowId": "wf-1",
                        "ExecutionStatus": 1,
                        "StartTime": "2026-08-31T18:00:00.000Z",
                    },
                }
            ]
        )

        self.assertEqual(
            kinds(table.dims),
            [
                ("_id", "category"),
                ("WorkflowId", "category"),
                ("ExecutionStatus", "number"),
                ("StartTime", "time"),
            ],
        )
        self.assertEqual(table.rows[0]["WorkflowId"], "wf-1")

    def test_nested_source_objects_are_dotted(self):
        table = es_viz.table_from_hits([{"_id": "a", "_source": {"outer": {"inner": 3}}}])

        self.assertEqual(table.rows[0]["outer.inner"], 3)

    def test_cat_records_infer_numeric_strings(self):
        table = es_viz.table_from_records(
            [
                {"index": "vis-1", "docs.count": "1200", "health": "green"},
                {"index": "vis-2", "docs.count": "80", "health": "green"},
            ]
        )

        self.assertEqual(
            kinds(table.dims) + kinds(table.measures),
            [("index", "category"), ("health", "category"), ("docs.count", "number")],
        )
        self.assertEqual(table.rows[0]["docs.count"], 1200.0)

    def test_flat_object_becomes_key_values(self):
        document = es_viz.build_document(
            {"cluster_name": "vis", "status": "green", "active_shards": 288}
        )

        self.assertEqual(document.tables, [])
        self.assertEqual(
            document.keyvalues,
            [("cluster_name", "vis"), ("status", "green"), ("active_shards", "288")],
        )

    def test_search_metadata_is_reported(self):
        document = es_viz.build_document(
            {
                "took": 239,
                "hits": {"total": {"value": 10000, "relation": "gte"}, "hits": []},
                "aggregations": {"by_ns": {"buckets": [{"key": "a", "doc_count": 1}]}},
            }
        )

        self.assertEqual([t.name for t in document.tables], ["by_ns"])
        self.assertEqual(dict(document.keyvalues)["took"], "239ms")
        self.assertEqual(dict(document.keyvalues)["hits.total"], "≥10000")

    def test_plain_text_response_is_rejected_with_a_hint(self):
        with self.assertRaises(SystemExit) as caught:
            es_viz.parse_input("health status index\ngreen open vis-1\n")

        self.assertIn("format=json", str(caught.exception))


class TestChartForm(unittest.TestCase):
    def form(self, dims, measures=("doc_count",), rows=None):
        table = es_viz.Table(
            name="t",
            dims=[es_viz.Column(name, kind) for name, kind in dims],
            measures=[es_viz.Column(name, "number") for name in measures],
            rows=rows or [],
        )
        return es_viz.chart_form(table)

    def test_no_dimensions_is_stat_tiles(self):
        self.assertEqual(self.form([]), "tiles")

    def test_one_category_dimension_is_horizontal_bars(self):
        self.assertEqual(self.form([("by_ns", "category")]), "bars")

    def test_one_time_dimension_is_columns(self):
        rows = [{"t": i} for i in range(24)]
        self.assertEqual(self.form([("by5m", "time")], rows=rows), "columns")

    def test_many_time_buckets_switch_to_a_line(self):
        rows = [{"t": i} for i in range(200)]
        self.assertEqual(self.form([("by5m", "time")], rows=rows), "lines")

    def test_time_plus_category_is_stacked_columns(self):
        rows = [{"t": i} for i in range(24)]
        self.assertEqual(
            self.form([("by5m", "time"), ("by_status", "category")], rows=rows),
            "columns",
        )

    def test_two_category_dimensions_are_a_heatmap(self):
        self.assertEqual(
            self.form([("by_ns", "category"), ("by_status", "category")]), "heatmap"
        )

    def test_three_dimensions_is_table_only(self):
        self.assertEqual(
            self.form(
                [("a", "category"), ("b", "category"), ("c", "category")],
            ),
            "table",
        )


class TestSeriesOrder(unittest.TestCase):
    def test_series_are_ordered_by_total_and_folded_into_other(self):
        rows = [{"s": f"s{i}", "doc_count": 100 - i} for i in range(12)]
        table = es_viz.Table(
            name="t",
            dims=[es_viz.Column("s", "category")],
            measures=[es_viz.Column("doc_count", "number")],
            rows=rows,
        )

        order = es_viz.series_order(table, "s", "doc_count")

        self.assertEqual(order[:7], [f"s{i}" for i in range(7)])
        self.assertEqual(order[7], "Other")
        self.assertEqual(len(order), 8)

    def test_few_series_are_not_folded(self):
        rows = [{"s": "a", "doc_count": 1}, {"s": "b", "doc_count": 2}]
        table = es_viz.Table(
            name="t",
            dims=[es_viz.Column("s", "category")],
            measures=[es_viz.Column("doc_count", "number")],
            rows=rows,
        )

        self.assertEqual(es_viz.series_order(table, "s", "doc_count"), ["b", "a"])


if __name__ == "__main__":
    unittest.main()
