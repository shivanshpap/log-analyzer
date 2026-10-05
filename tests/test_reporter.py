"""Unit tests for reporter modules (ConsoleReporter and JsonReporter)."""

import json
from datetime import datetime
from collections import Counter
from src.models import AnalysisStats, LogEntry, FilterCriteria
from src.reporter import ConsoleReporter, JsonReporter


class TestReporter:
    """Test suite for report generation in console and JSON formats."""

    def test_json_report_structure(self):
        stats = AnalysisStats(
            total_lines_read=100,
            valid_entries_count=95,
            malformed_entries_count=5,
            filtered_entries_count=20,
            level_counts=Counter({"INFO": 10, "WARNING": 5, "ERROR": 5}),
            top_errors=[("Connection timeout", 5)],
            earliest_timestamp=datetime(2026, 9, 30, 10, 0, 0),
            latest_timestamp=datetime(2026, 9, 30, 11, 0, 0),
        )
        criteria = FilterCriteria(levels={"ERROR"})

        json_str = JsonReporter.to_json_string(stats, "app.log", criteria)
        data = json.loads(json_str)

        assert "summary" in data
        assert data["summary"]["total_lines_read"] == 100
        assert data["summary"]["valid_entries_count"] == 95
        assert data["summary"]["malformed_entries_count"] == 5
        assert "level_distribution" in data
        assert data["level_distribution"]["ERROR"] == 5
        assert len(data["top_errors"]) == 1
        assert data["top_errors"][0]["message"] == "Connection timeout"
        assert data["metadata"]["file_path"] == "app.log"

    def test_json_file_export(self, tmp_path):
        stats = AnalysisStats(total_lines_read=10, valid_entries_count=10)
        output_file = tmp_path / "subdir" / "test_report.json"

        JsonReporter.save_to_file(stats, "test.log", str(output_file))

        assert output_file.exists()
        loaded = json.loads(output_file.read_text(encoding="utf-8"))
        assert loaded["summary"]["total_lines_read"] == 10

    def test_console_reporter_plain_and_rich(self, capsys):
        stats = AnalysisStats(
            total_lines_read=5,
            valid_entries_count=5,
            level_counts=Counter({"ERROR": 2, "INFO": 3}),
            top_errors=[("Test error", 2)],
        )

        reporter = ConsoleReporter(force_plain=True)
        reporter.print_report(stats, "test.log")
        out, _ = capsys.readouterr()
        assert "LOG FILE ANALYSIS & DIAGNOSTICS REPORT" in out
        assert "Total Lines Scanned:" in out

        # Test Rich console path
        rich_reporter = ConsoleReporter(force_plain=False)
        rich_reporter.print_report(stats, "test.log")
