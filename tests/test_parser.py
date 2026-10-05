"""Unit tests for the log parsing module."""

import pytest
from datetime import datetime
from src.parser import LogParser
from src.models import LogEntry


class TestLogParser:
    """Test suite for LogParser functionality."""

    @pytest.fixture
    def parser(self) -> LogParser:
        return LogParser()

    def test_parse_standard_python_log(self, parser: LogParser):
        line = "2026-09-30 14:23:45,123 - ERROR - [auth_service] - Invalid credentials for user"
        entry = parser.parse_line(line, line_number=1)

        assert entry.is_valid is True
        assert entry.line_number == 1
        assert entry.level == "ERROR"
        assert entry.logger_name == "auth_service"
        assert "Invalid credentials for user" in entry.message
        assert entry.timestamp == datetime(2026, 9, 30, 14, 23, 45, 123000)

    def test_parse_bracketed_format(self, parser: LogParser):
        line = "[2026-09-30 15:10:00] [WARNING] [db_pool] Connection pool at 85% capacity"
        entry = parser.parse_line(line, line_number=5)

        assert entry.is_valid is True
        assert entry.level == "WARNING"
        assert entry.logger_name == "db_pool"
        assert entry.message == "Connection pool at 85% capacity"
        assert entry.timestamp == datetime(2026, 9, 30, 15, 10, 0)

    def test_parse_iso8601_format(self, parser: LogParser):
        line = "2026-09-30T16:05:22.500000Z INFO Server listening on port 8080"
        entry = parser.parse_line(line, line_number=10)

        assert entry.is_valid is True
        assert entry.level == "INFO"
        assert "Server listening on port 8080" in entry.message
        assert entry.timestamp is not None
        assert entry.timestamp.year == 2026
        assert entry.timestamp.month == 9
        assert entry.timestamp.hour == 16

    def test_level_normalization(self, parser: LogParser):
        line_warn = "2026-09-30 12:00:00 - WARN - Disk running low"
        entry_warn = parser.parse_line(line_warn)
        assert entry_warn.level == "WARNING"

        line_fatal = "2026-09-30 12:00:00 - FATAL - Kernel panic"
        entry_fatal = parser.parse_line(line_fatal)
        assert entry_fatal.level == "CRITICAL"

    def test_invalid_malformed_lines(self, parser: LogParser):
        # Empty string
        entry_empty = parser.parse_line("", line_number=1)
        assert entry_empty.is_valid is False
        assert "Empty" in entry_empty.error_reason

        # Corrupt text
        entry_corrupt = parser.parse_line("Random unparseable garbage text", line_number=2)
        assert entry_corrupt.is_valid is False
        assert entry_corrupt.error_reason is not None

        # Invalid log level
        entry_bad_level = parser.parse_line("2026-09-30 12:00:00 - UNKNOWNLEVEL - Something happened", line_number=3)
        assert entry_bad_level.is_valid is False

    def test_custom_regex_pattern(self):
        custom_pat = r"^(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \| (?P<level>\w+) \| (?P<message>.*)$"
        custom_parser = LogParser(custom_pattern=custom_pat)

        line = "2026/09/30 18:30:00 | ERROR | Custom pipeline crash"
        entry = custom_parser.parse_line(line)

        assert entry.is_valid is True
        assert entry.level == "ERROR"
        assert entry.message == "Custom pipeline crash"
        assert entry.timestamp == datetime(2026, 9, 30, 18, 30, 0)

    def test_multiline_traceback_combining(self, tmp_path):
        log_content = (
            "2026-09-30 10:00:00 - INFO - Started task\n"
            "2026-09-30 10:00:01 - ERROR - Task failed with exception\n"
            "Traceback (most recent call last):\n"
            "  File 'test.py', line 10, in run\n"
            "ValueError: Invalid value\n"
            "2026-09-30 10:00:02 - INFO - Task cleanup finished\n"
        )
        file_path = tmp_path / "test_trace.log"
        file_path.write_text(log_content, encoding="utf-8")

        parser = LogParser(combine_multiline=True)
        entries = list(parser.parse_file(file_path))

        assert len(entries) == 3
        assert entries[0].level == "INFO"
        assert entries[1].level == "ERROR"
        assert "ValueError: Invalid value" in entries[1].message
        assert "Traceback" in entries[1].message
        assert entries[2].level == "INFO"

    def test_file_not_found(self, parser: LogParser):
        with pytest.raises(FileNotFoundError):
            list(parser.parse_file("non_existent_file_xyz_123.log"))
