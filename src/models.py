"""Data models for log entries, filtering criteria, and analysis statistics."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Set, List, Tuple, Dict, Any
from collections import Counter


@dataclass
class LogEntry:
    """Represents a single parsed log entry."""
    line_number: int
    raw_line: str
    timestamp: Optional[datetime] = None
    level: str = "UNKNOWN"
    message: str = ""
    logger_name: Optional[str] = None
    is_valid: bool = True
    error_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to a JSON-serializable dictionary."""
        return {
            "line_number": self.line_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "logger_name": self.logger_name,
            "message": self.message,
            "is_valid": self.is_valid,
            "error_reason": self.error_reason,
            "raw_line": self.raw_line if not self.is_valid else None
        }


@dataclass
class FilterCriteria:
    """Criteria used for filtering log entries."""
    levels: Optional[Set[str]] = None
    keyword: Optional[str] = None
    case_sensitive: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def is_active(self) -> bool:
        """Return True if any filter criteria is active."""
        return bool(self.levels or self.keyword or self.start_time or self.end_time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert criteria to a serializable dictionary."""
        return {
            "levels": sorted(list(self.levels)) if self.levels else None,
            "keyword": self.keyword,
            "case_sensitive": self.case_sensitive,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class AnalysisStats:
    """Aggregated statistics resulting from log analysis."""
    total_lines_read: int = 0
    valid_entries_count: int = 0
    malformed_entries_count: int = 0
    filtered_entries_count: int = 0
    level_counts: Counter = field(default_factory=Counter)
    top_errors: List[Tuple[str, int]] = field(default_factory=list)
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    sample_malformed_entries: List[Dict[str, Any]] = field(default_factory=list)
    ai_insights: Optional[Dict[str, Any]] = None

    @property
    def error_rate(self) -> float:
        """Calculate the percentage of log entries that are ERROR or CRITICAL."""
        total_eval = self.filtered_entries_count if self.filtered_entries_count > 0 else self.valid_entries_count
        if total_eval == 0:
            return 0.0
        error_count = self.level_counts.get("ERROR", 0) + self.level_counts.get("CRITICAL", 0)
        return round((error_count / total_eval) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis statistics to a JSON-serializable dictionary."""
        duration_seconds = None
        if self.earliest_timestamp and self.latest_timestamp:
            duration_seconds = (self.latest_timestamp - self.earliest_timestamp).total_seconds()

        return {
            "summary": {
                "total_lines_read": self.total_lines_read,
                "valid_entries_count": self.valid_entries_count,
                "malformed_entries_count": self.malformed_entries_count,
                "filtered_entries_count": self.filtered_entries_count,
                "error_rate_percentage": self.error_rate,
                "earliest_timestamp": self.earliest_timestamp.isoformat() if self.earliest_timestamp else None,
                "latest_timestamp": self.latest_timestamp.isoformat() if self.latest_timestamp else None,
                "duration_seconds": duration_seconds,
            },
            "level_distribution": dict(self.level_counts),
            "top_errors": [
                {"message": msg, "count": count}
                for msg, count in self.top_errors
            ],
            "sample_malformed_entries": self.sample_malformed_entries,
            "ai_insights": self.ai_insights
        }
