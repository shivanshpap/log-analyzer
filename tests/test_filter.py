"""Unit tests for the log filtering module."""

import pytest
from datetime import datetime
from src.models import LogEntry
from src.filter import LogFilter


class TestLogFilter:
    """Test suite for LogFilter matching and streaming."""

    @pytest.fixture
    def sample_entries(self):
        return [
            LogEntry(
                line_number=1,
                raw_line="",
                timestamp=datetime(2026, 9, 30, 10, 0, 0),
                level="INFO",
                logger_name="auth",
                message="User login succeeded",
            ),
            LogEntry(
                line_number=2,
                raw_line="",
                timestamp=datetime(2026, 9, 30, 10, 15, 0),
                level="WARNING",
                logger_name="db",
                message="Slow query detected: 1200ms",
            ),
            LogEntry(
                line_number=3,
                raw_line="",
                timestamp=datetime(2026, 9, 30, 10, 30, 0),
                level="ERROR",
                logger_name="db",
                message="Connection timeout connecting to postgres",
            ),
            LogEntry(
                line_number=4,
                raw_line="",
                timestamp=datetime(2026, 9, 30, 11, 0, 0),
                level="CRITICAL",
                logger_name="system",
                message="Out of memory detected",
            ),
            LogEntry(
                line_number=5,
                raw_line="MALFORMED",
                timestamp=None,
                level="UNKNOWN",
                message="malformed line",
                is_valid=False,
            ),
        ]

    def test_filter_by_single_level(self, sample_entries):
        filter_error = LogFilter.create(levels="ERROR")
        results = list(filter_error.filter_entries(sample_entries))

        assert len(results) == 1
        assert results[0].level == "ERROR"
        assert results[0].line_number == 3

    def test_filter_by_multiple_levels(self, sample_entries):
        filter_multi = LogFilter.create(levels="WARNING,CRITICAL")
        results = list(filter_multi.filter_entries(sample_entries))

        assert len(results) == 2
        levels = [r.level for r in results]
        assert "WARNING" in levels
        assert "CRITICAL" in levels

    def test_filter_by_keyword_case_insensitive(self, sample_entries):
        filter_kw = LogFilter.create(keyword="timeout")
        results = list(filter_kw.filter_entries(sample_entries))

        assert len(results) == 1
        assert "timeout" in results[0].message.lower()

    def test_filter_by_keyword_in_logger_name(self, sample_entries):
        filter_logger = LogFilter.create(keyword="auth")
        results = list(filter_logger.filter_entries(sample_entries))

        assert len(results) == 1
        assert results[0].logger_name == "auth"

    def test_filter_by_keyword_case_sensitive(self, sample_entries):
        filter_match = LogFilter.create(keyword="Postgres", case_sensitive=True)
        results_match = list(filter_match.filter_entries(sample_entries))
        assert len(results_match) == 0  # "postgres" is lowercase in message

        filter_exact = LogFilter.create(keyword="postgres", case_sensitive=True)
        results_exact = list(filter_exact.filter_entries(sample_entries))
        assert len(results_exact) == 1

    def test_filter_by_time_window(self, sample_entries):
        start = datetime(2026, 9, 30, 10, 10, 0)
        end = datetime(2026, 9, 30, 10, 45, 0)
        time_filter = LogFilter.create(start_time=start, end_time=end)

        results = list(time_filter.filter_entries(sample_entries))
        assert len(results) == 2
        assert results[0].line_number == 2
        assert results[1].line_number == 3

    def test_combined_filters(self, sample_entries):
        # Level ERROR + keyword "postgres"
        combo_filter = LogFilter.create(levels="ERROR", keyword="postgres")
        results = list(combo_filter.filter_entries(sample_entries))

        assert len(results) == 1
        assert results[0].line_number == 3

        # Level ERROR + keyword "login" (should be 0 matches)
        no_match_filter = LogFilter.create(levels="ERROR", keyword="login")
        no_matches = list(no_match_filter.filter_entries(sample_entries))
        assert len(no_matches) == 0

    def test_malformed_entries_ignored_by_active_filter(self, sample_entries):
        filt = LogFilter.create(levels="INFO")
        results = list(filt.filter_entries(sample_entries))
        for r in results:
            assert r.is_valid is True
