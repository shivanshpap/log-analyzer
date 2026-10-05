"""Log parsing module using regular expressions for efficient, robust log ingestion."""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, List, Pattern, Union
from dateutil import parser as dateutil_parser

from src.models import LogEntry

logger = logging.getLogger("LogAnalyzer.Parser")

# Standard recognized log levels
KNOWN_LEVELS = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"}

LEVEL_NORMALIZATION = {
    "WARN": "WARNING",
    "FATAL": "CRITICAL",
}

# Default list of regular expression patterns to match various common application log formats
DEFAULT_PATTERNS = [
    # 1. Bracketed timestamp and/or bracketed level:
    # [2026-09-30 14:23:45] [ERROR] [auth] Invalid credentials
    # [2026-09-30 14:23:45] ERROR: Invalid credentials
    re.compile(
        r"^\[(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\]\s*"
        r"(?:\[(?P<level>[A-Za-z]+)\]|(?P<level_alt>[A-Za-z]+):?)\s*"
        r"(?:\[(?P<logger>[\w\.\-]+)\]\s*[:-]?\s*)?"
        r"(?P<message>.*)$"
    ),
    # 2. Standard timestamp with hyphen or space delimiters:
    # 2026-09-30 14:23:45,123 - ERROR - [auth] - Invalid credentials
    # 2026-09-30 14:23:45 - ERROR - Invalid credentials
    # 2026-09-30 14:23:45 ERROR: Invalid credentials
    re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s*"
        r"(?:[-|:]\s*)?"
        r"\[?(?P<level>[A-Za-z]+)\]?\s*"
        r"(?:[-|:]\s*)?"
        r"(?:\[?(?P<logger>[\w\.\-]+)\]?\s*[-|:]\s*)?"
        r"(?P<message>.*)$"
    ),
    # 3. ISO-8601 strict format:
    # 2026-09-30T14:23:45.123456Z ERROR Invalid credentials
    re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
        r"(?P<level>[A-Za-z]+)\s+"
        r"(?:(?P<logger>[\w\.\-]+)\s+[-:]\s+)?"
        r"(?P<message>.*)$"
    ),
]


class LogParser:
    """Parses application log lines and files into structured LogEntry objects."""

    def __init__(
        self,
        custom_pattern: Optional[str] = None,
        combine_multiline: bool = True,
    ) -> None:
        """
        Initialize the log parser.

        Args:
            custom_pattern: Optional regex pattern string with named groups
                            'timestamp', 'level', 'message', and optionally 'logger'.
            combine_multiline: If True, multi-line error traces (e.g. Python tracebacks)
                              are appended to the parent entry's message.
        """
        self.combine_multiline = combine_multiline
        self.compiled_custom_pattern: Optional[Pattern[str]] = None
        if custom_pattern:
            try:
                self.compiled_custom_pattern = re.compile(custom_pattern)
                logger.debug("Loaded custom regex pattern: %s", custom_pattern)
            except re.error as exc:
                logger.error("Failed to compile custom regex pattern: %s", exc)
                raise ValueError(f"Invalid custom regex pattern: {exc}") from exc

    def _normalize_level(self, level_str: str) -> str:
        """Normalize log level string to standard naming (e.g., WARN -> WARNING)."""
        upper = level_str.strip().upper()
        return LEVEL_NORMALIZATION.get(upper, upper)

    def _parse_timestamp(self, ts_str: str) -> Optional[datetime]:
        """Parse timestamp string using fast-paths or fallback to dateutil."""
        ts_clean = ts_str.strip().replace(",", ".")
        # Fast path for common formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(ts_clean, fmt)
            except ValueError:
                continue

        # Fallback to dateutil for ISO-8601 with tz or timezone offsets
        try:
            return dateutil_parser.parse(ts_clean)
        except (ValueError, TypeError, OverflowError) as exc:
            logger.debug("Failed to parse timestamp '%s': %s", ts_str, exc)
            return None

    def parse_line(self, line: str, line_number: int = 1) -> LogEntry:
        """
        Parse a single line into a LogEntry.

        Args:
            line: Raw log line string.
            line_number: Line number in the source file.

        Returns:
            LogEntry with parsed fields or flagged as invalid.
        """
        stripped = line.rstrip("\r\n")

        # Empty lines are considered invalid/empty
        if not stripped.strip():
            return LogEntry(
                line_number=line_number,
                raw_line=stripped,
                is_valid=False,
                error_reason="Empty or whitespace-only line",
            )

        match = None
        if self.compiled_custom_pattern:
            match = self.compiled_custom_pattern.search(stripped)
        else:
            for pattern in DEFAULT_PATTERNS:
                m = pattern.search(stripped)
                if m:
                    match = m
                    break

        if not match:
            return LogEntry(
                line_number=line_number,
                raw_line=stripped,
                is_valid=False,
                error_reason="Line does not match recognized log format",
            )

        groups = match.groupdict()
        ts_raw = groups.get("timestamp")
        level_raw = groups.get("level") or groups.get("level_alt")
        message_raw = groups.get("message", "")
        logger_name = groups.get("logger")

        if not ts_raw or not level_raw:
            return LogEntry(
                line_number=line_number,
                raw_line=stripped,
                is_valid=False,
                error_reason="Missing required timestamp or level field",
            )

        norm_level = self._normalize_level(level_raw)
        if norm_level not in KNOWN_LEVELS:
            # If the extracted level isn't a known log level, mark invalid
            return LogEntry(
                line_number=line_number,
                raw_line=stripped,
                is_valid=False,
                error_reason=f"Unrecognized log level '{level_raw}'",
            )

        parsed_ts = self._parse_timestamp(ts_raw)
        if not parsed_ts:
            return LogEntry(
                line_number=line_number,
                raw_line=stripped,
                is_valid=False,
                error_reason=f"Unable to parse timestamp '{ts_raw}'",
            )

        return LogEntry(
            line_number=line_number,
            raw_line=stripped,
            timestamp=parsed_ts,
            level=norm_level,
            message=message_raw.strip(),
            logger_name=logger_name.strip() if logger_name else None,
            is_valid=True,
        )

    def parse_file(
        self, file_path: Union[str, Path]
    ) -> Generator[LogEntry, None, None]:
        """
        Stream and parse a log file line-by-line efficiently.

        Args:
            file_path: Path to the log file to read.

        Yields:
            LogEntry objects as they are parsed.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        logger.info("Starting streaming parse of %s", path)
        pending_entry: Optional[LogEntry] = None

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_idx, line in enumerate(f, start=1):
                entry = self.parse_line(line, line_number=line_idx)

                if self.combine_multiline:
                    if entry.is_valid:
                        if pending_entry is not None:
                            yield pending_entry
                        pending_entry = entry
                    else:
                        # If invalid, check if this is continuation of previous entry (e.g. stack trace)
                        # Continuation lines typically start with spaces/tabs or "Traceback" or exception text
                        if pending_entry is not None and (
                            line.startswith(" ")
                            or line.startswith("\t")
                            or "Traceback" in line
                            or "Error:" in line
                            or "Exception:" in line
                        ):
                            pending_entry.message += f"\n{entry.raw_line}"
                        else:
                            if pending_entry is not None:
                                yield pending_entry
                                pending_entry = None
                            yield entry
                else:
                    yield entry

            if pending_entry is not None:
                yield pending_entry

        logger.info("Finished streaming parse of %s", path)
