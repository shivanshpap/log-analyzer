"""Filtering module for log entries based on level, keyword, and time ranges."""

import logging
from datetime import datetime
from typing import Generator, Iterable, Optional, Set, Union
from dateutil import parser as dateutil_parser

from src.models import LogEntry, FilterCriteria

logger = logging.getLogger("LogAnalyzer.Filter")


class LogFilter:
    """Filters parsed log entries based on configurable criteria."""

    def __init__(self, criteria: Optional[FilterCriteria] = None) -> None:
        """
        Initialize the filter with optional criteria.

        Args:
            criteria: FilterCriteria specifying level, keyword, and time window.
        """
        self.criteria = criteria or FilterCriteria()
        # Pre-normalize levels if provided
        if self.criteria.levels:
            self.normalized_levels: Set[str] = {
                lvl.strip().upper() for lvl in self.criteria.levels
            }
        else:
            self.normalized_levels = set()

    @classmethod
    def create(
        cls,
        levels: Optional[Union[str, Iterable[str]]] = None,
        keyword: Optional[str] = None,
        case_sensitive: bool = False,
        start_time: Optional[Union[str, datetime]] = None,
        end_time: Optional[Union[str, datetime]] = None,
    ) -> "LogFilter":
        """
        Factory helper to create a LogFilter with string or datetime inputs.

        Args:
            levels: Single level string, comma-separated string, or collection of levels.
            keyword: Substring to search for in log message.
            case_sensitive: Whether keyword matching should be case-sensitive.
            start_time: Start of time window (ISO string, date string, or datetime).
            end_time: End of time window (ISO string, date string, or datetime).
        """
        level_set: Optional[Set[str]] = None
        if levels:
            if isinstance(levels, str):
                level_set = {l.strip().upper() for l in levels.split(",") if l.strip()}
            else:
                level_set = {l.strip().upper() for l in levels}

        parsed_start: Optional[datetime] = None
        if start_time:
            if isinstance(start_time, datetime):
                parsed_start = start_time
            else:
                parsed_start = dateutil_parser.parse(str(start_time).strip())

        parsed_end: Optional[datetime] = None
        if end_time:
            if isinstance(end_time, datetime):
                parsed_end = end_time
            else:
                parsed_end = dateutil_parser.parse(str(end_time).strip())

        criteria = FilterCriteria(
            levels=level_set,
            keyword=keyword,
            case_sensitive=case_sensitive,
            start_time=parsed_start,
            end_time=parsed_end,
        )
        return cls(criteria=criteria)

    def matches(self, entry: LogEntry) -> bool:
        """
        Check if a single LogEntry satisfies all active filter criteria.

        Args:
            entry: LogEntry to evaluate.

        Returns:
            True if entry matches all active filters, False otherwise.
        """
        # If entry is malformed or invalid, filter only applies if no specific criteria match
        if not entry.is_valid:
            return False

        # 1. Level Filter
        if self.normalized_levels and entry.level.upper() not in self.normalized_levels:
            return False

        # 2. Timestamp Window Filter
        if self.criteria.start_time or self.criteria.end_time:
            if not entry.timestamp:
                return False
            # Normalize comparisons if one is naive and one is aware
            entry_ts = entry.timestamp
            start_ts = self.criteria.start_time
            end_ts = self.criteria.end_time

            if start_ts:
                if entry_ts.tzinfo is not None and start_ts.tzinfo is None:
                    start_ts = start_ts.replace(tzinfo=entry_ts.tzinfo)
                elif entry_ts.tzinfo is None and start_ts.tzinfo is not None:
                    entry_ts = entry_ts.replace(tzinfo=start_ts.tzinfo)
                if entry_ts < start_ts:
                    return False

            if end_ts:
                if entry_ts.tzinfo is not None and end_ts.tzinfo is None:
                    end_ts = end_ts.replace(tzinfo=entry_ts.tzinfo)
                elif entry_ts.tzinfo is None and end_ts.tzinfo is not None:
                    entry_ts = entry_ts.replace(tzinfo=end_ts.tzinfo)
                if entry_ts > end_ts:
                    return False

        # 3. Keyword Filter
        if self.criteria.keyword:
            kw = self.criteria.keyword
            msg = entry.message
            logger_name = entry.logger_name or ""
            target_text = f"{logger_name} {msg}"

            if not self.criteria.case_sensitive:
                if kw.lower() not in target_text.lower():
                    return False
            else:
                if kw not in target_text:
                    return False

        return True

    def filter_entries(
        self, entries: Iterable[LogEntry]
    ) -> Generator[LogEntry, None, None]:
        """
        Stream filtered log entries from an iterable.

        Args:
            entries: Stream of LogEntry objects.

        Yields:
            LogEntry objects matching active filter criteria.
        """
        if not self.criteria.is_active():
            yield from entries
            return

        for entry in entries:
            if self.matches(entry):
                yield entry
