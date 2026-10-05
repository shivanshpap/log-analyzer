"""Unit tests for the log analyzer statistics and error aggregation module."""

import pytest
from datetime import datetime
from src.models import LogEntry
from src.analyzer import LogAnalyzer, normalize_error_message


class TestLogAnalyzer:
    """Test suite for LogAnalyzer aggregation and error frequency detection."""

    @pytest.fixture
    def stream_entries(self):
        return [
            LogEntry(1, "", datetime(2026, 9, 30, 10, 0, 0), "INFO", "User login"),
            LogEntry(2, "", datetime(2026, 9, 30, 10, 1, 0), "INFO", "Data fetch"),
            LogEntry(3, "", datetime(2026, 9, 30, 10, 2, 0), "WARNING", "Slow query"),
            LogEntry(4, "", datetime(2026, 9, 30, 10, 3, 0), "ERROR", "Connection refused: host=192.168.1.10:5432"),
            LogEntry(5, "", datetime(2026, 9, 30, 10, 4, 0), "ERROR", "Connection refused: host=192.168.1.20:5432"),
            LogEntry(6, "", datetime(2026, 9, 30, 10, 5, 0), "ERROR", "Read timeout after 5000ms"),
            LogEntry(7, "", datetime(2026, 9, 30, 10, 6, 0), "CRITICAL", "Out of memory"),
            LogEntry(8, "BAD_LINE", None, "UNKNOWN", "corrupt", is_valid=False, error_reason="Bad format"),
        ]

    def test_basic_counts(self, stream_entries):
        analyzer = LogAnalyzer()
        stats, _ = analyzer.analyze(stream_entries)

        assert stats.total_lines_read == 8
        assert stats.valid_entries_count == 7
        assert stats.malformed_entries_count == 1
        assert stats.level_counts["INFO"] == 2
        assert stats.level_counts["WARNING"] == 1
        assert stats.level_counts["ERROR"] == 3
        assert stats.level_counts["CRITICAL"] == 1

    def test_error_normalization_and_ranking(self, stream_entries):
        analyzer = LogAnalyzer(top_n_errors=5, normalize_errors=True)
        stats, _ = analyzer.analyze(stream_entries)

        # Connection refused: host=<IP:PORT> appeared twice, so it should be rank 1
        assert len(stats.top_errors) > 0
        top_error_pattern, count = stats.top_errors[0]
        assert "Connection refused" in top_error_pattern
        assert count == 2

    def test_timestamps_span(self, stream_entries):
        analyzer = LogAnalyzer()
        stats, _ = analyzer.analyze(stream_entries)

        assert stats.earliest_timestamp == datetime(2026, 9, 30, 10, 0, 0)
        assert stats.latest_timestamp == datetime(2026, 9, 30, 10, 6, 0)

    def test_error_rate_calculation(self, stream_entries):
        analyzer = LogAnalyzer()
        stats, _ = analyzer.analyze(stream_entries)

        # 3 ERROR + 1 CRITICAL = 4 error entries out of 7 valid entries = 57.14%
        assert stats.error_rate == 57.14

    def test_normalize_error_patterns(self):
        msg1 = "Connection failed to 10.0.0.5:8080 after 3 retries"
        norm1 = normalize_error_message(msg1)
        assert "<IP:PORT>" in norm1

        msg2 = "Transaction failed for user c4b37d89-9a21-4f8e-8e65-27a1b415a720"
        norm2 = normalize_error_message(msg2)
        assert "<UUID>" in norm2

    def test_empty_log_stream(self):
        analyzer = LogAnalyzer()
        stats, _ = analyzer.analyze([])

        assert stats.total_lines_read == 0
        assert stats.valid_entries_count == 0
        assert stats.error_rate == 0.0
        assert stats.top_errors == []
