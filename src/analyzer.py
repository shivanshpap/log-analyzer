"""Log analyzer module for streaming statistical aggregation and error analysis."""

import re
import logging
from collections import Counter
from typing import Generator, Iterable, List, Optional, Tuple, Dict, Any
from datetime import datetime

from src.models import LogEntry, AnalysisStats, FilterCriteria
from src.filter import LogFilter

logger = logging.getLogger("LogAnalyzer.Analyzer")

# Regex to normalize dynamic values (UUIDs, IP addresses, IDs, hex addresses) in error messages for grouping
RE_UUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
RE_IP = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?\b")
RE_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
RE_NUM = re.compile(r"\b\d{4,}\b")


def normalize_error_message(message: str) -> str:
    """
    Normalize dynamic parts of an error message to group similar errors together.
    Extracts the primary error summary line and masks IDs, IPs, and UUIDs.
    """
    first_line = message.split("\n", 1)[0].strip()
    norm = RE_UUID.sub("<UUID>", first_line)
    norm = RE_IP.sub("<IP:PORT>", norm)
    norm = RE_HEX.sub("<HEX>", norm)
    norm = RE_NUM.sub("<ID>", norm)
    return norm


class LogAnalyzer:
    """Performs statistical analysis, frequency counts, and error detection over log entries."""

    def __init__(self, top_n_errors: int = 5, normalize_errors: bool = True) -> None:
        """
        Initialize the analyzer.

        Args:
            top_n_errors: Number of top error messages to report.
            normalize_errors: Whether to group similar errors by masking dynamic IDs.
        """
        self.top_n_errors = top_n_errors
        self.normalize_errors = normalize_errors

    def analyze(
        self,
        entries: Iterable[LogEntry],
        log_filter: Optional[LogFilter] = None,
        collect_filtered_entries: bool = False,
    ) -> Tuple[AnalysisStats, List[LogEntry]]:
        """
        Analyze a stream of LogEntry objects in a single pass with O(1) memory overhead.

        Args:
            entries: Iterable / generator of LogEntry objects.
            log_filter: Optional filter to apply during analysis.
            collect_filtered_entries: If True, returns the list of matched entries.

        Returns:
            Tuple of (AnalysisStats, list of matched entries).
        """
        stats = AnalysisStats()
        error_counter: Counter = Counter()
        matched_entries: List[LogEntry] = []
        is_filtering = log_filter is not None and log_filter.criteria.is_active()

        for entry in entries:
            stats.total_lines_read += 1

            if not entry.is_valid:
                stats.malformed_entries_count += 1
                if len(stats.sample_malformed_entries) < 10:
                    stats.sample_malformed_entries.append({
                        "line_number": entry.line_number,
                        "raw_line": entry.raw_line,
                        "reason": entry.error_reason,
                    })
                continue

            stats.valid_entries_count += 1

            # Update overall timeline tracking for valid entries
            if entry.timestamp:
                if stats.earliest_timestamp is None or entry.timestamp < stats.earliest_timestamp:
                    stats.earliest_timestamp = entry.timestamp
                if stats.latest_timestamp is None or entry.timestamp > stats.latest_timestamp:
                    stats.latest_timestamp = entry.timestamp

            # Evaluate filter criteria
            if is_filtering:
                assert log_filter is not None
                if not log_filter.matches(entry):
                    continue

            # Process entry for statistics
            stats.filtered_entries_count += 1
            stats.level_counts[entry.level] += 1

            if entry.level in ("ERROR", "CRITICAL"):
                err_key = (
                    normalize_error_message(entry.message)
                    if self.normalize_errors
                    else entry.message.split("\n", 1)[0].strip()
                )
                error_counter[err_key] += 1

            if collect_filtered_entries:
                matched_entries.append(entry)

        stats.top_errors = error_counter.most_common(self.top_n_errors)
        logger.info(
            "Analysis complete. Total lines: %d, Valid: %d, Malformed: %d, Matched: %d",
            stats.total_lines_read,
            stats.valid_entries_count,
            stats.malformed_entries_count,
            stats.filtered_entries_count,
        )
        return stats, matched_entries
