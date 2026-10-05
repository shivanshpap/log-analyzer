"""Report generation module for formatting console (Rich and plain-text) and JSON outputs."""

import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.models import AnalysisStats, LogEntry, FilterCriteria

logger = logging.getLogger("LogAnalyzer.Reporter")

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


LEVEL_STYLES = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "WARN": "yellow",
    "ERROR": "bold red",
    "CRITICAL": "bold magenta",
    "FATAL": "bold magenta",
}


class ConsoleReporter:
    """Renders human-readable summary reports in the terminal using Rich or plain text."""

    def __init__(self, force_plain: bool = False) -> None:
        self.use_rich = RICH_AVAILABLE and not force_plain
        if self.use_rich:
            try:
                self.console = Console(legacy_windows=False)
            except Exception:
                self.console = Console()

    def print_report(
        self,
        stats: AnalysisStats,
        file_path: str,
        filter_criteria: Optional[FilterCriteria] = None,
        top_entries: Optional[List[LogEntry]] = None,
    ) -> None:
        """Print full console report."""
        if self.use_rich:
            self._print_rich_report(stats, file_path, filter_criteria, top_entries)
        else:
            self._print_plain_report(stats, file_path, filter_criteria, top_entries)

    def _print_rich_report(
        self,
        stats: AnalysisStats,
        file_path: str,
        filter_criteria: Optional[FilterCriteria] = None,
        top_entries: Optional[List[LogEntry]] = None,
    ) -> None:
        console = self.console

        # Header Title
        console.print(Panel(
            "[bold white]LOG FILE ANALYSIS & DIAGNOSTICS REPORT[/bold white]",
            style="bold cyan",
            expand=False,
        ))

        # 1. Summary Information Table
        summary_table = Table(box=box.ROUNDED, show_header=False, title="Summary Overview")
        summary_table.add_column("Property", style="bold cyan", width=26)
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Log File Path", str(file_path))
        summary_table.add_row("Total Lines Scanned", f"{stats.total_lines_read:,}")
        summary_table.add_row("Valid Log Entries", f"[green]{stats.valid_entries_count:,}[/green]")
        summary_table.add_row(
            "Malformed / Corrupt Lines",
            f"[red]{stats.malformed_entries_count:,}[/red]" if stats.malformed_entries_count > 0 else "0"
        )

        if filter_criteria and filter_criteria.is_active():
            summary_table.add_row("Filtered Entries Matched", f"[yellow]{stats.filtered_entries_count:,}[/yellow]")
            filters_desc = []
            if filter_criteria.levels:
                filters_desc.append(f"Levels: {', '.join(sorted(filter_criteria.levels))}")
            if filter_criteria.keyword:
                filters_desc.append(f"Keyword: '{filter_criteria.keyword}'")
            if filter_criteria.start_time:
                filters_desc.append(f"From: {filter_criteria.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if filter_criteria.end_time:
                filters_desc.append(f"To: {filter_criteria.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            summary_table.add_row("Active Filter Criteria", " | ".join(filters_desc))

        if stats.earliest_timestamp and stats.latest_timestamp:
            summary_table.add_row("Time Window Start", stats.earliest_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            summary_table.add_row("Time Window End", stats.latest_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            duration = stats.latest_timestamp - stats.earliest_timestamp
            summary_table.add_row("Total Time Span", str(duration))

        summary_table.add_row("Error & Critical Rate", f"[bold red]{stats.error_rate}%[/bold red]")
        console.print(summary_table)

        # 2. Log Level Distribution Table
        level_table = Table(box=box.ROUNDED, title="Log Level Distribution")
        level_table.add_column("Level", style="bold", width=14)
        level_table.add_column("Count", justify="right", width=12)
        level_table.add_column("Percentage", justify="right", width=14)
        level_table.add_column("Visual Distribution", width=30)

        total_valid = stats.filtered_entries_count if stats.filtered_entries_count > 0 else (stats.valid_entries_count or 1)
        priority_levels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
        all_levels = sorted(
            stats.level_counts.keys(),
            key=lambda l: priority_levels.index(l) if l in priority_levels else 99
        )

        for lvl in all_levels:
            count = stats.level_counts[lvl]
            pct = (count / total_valid) * 100 if total_valid > 0 else 0.0
            color = LEVEL_STYLES.get(lvl, "white")
            bar_len = int((pct / 100.0) * 25)
            bar = "#" * bar_len + "-" * (25 - bar_len)
            level_table.add_row(
                f"[{color}]{lvl}[/{color}]",
                f"{count:,}",
                f"{pct:.1f}%",
                f"[{color}]{bar}[/{color}]"
            )

        console.print(level_table)

        # 3. Top Most Common Error Messages
        if stats.top_errors:
            error_table = Table(box=box.ROUNDED, title="Top Most Common Error Messages")
            error_table.add_column("#", justify="center", width=4, style="dim")
            error_table.add_column("Count", justify="right", width=10, style="bold red")
            error_table.add_column("Error Message Pattern", style="white")

            for rank, (msg, count) in enumerate(stats.top_errors, start=1):
                error_table.add_row(str(rank), f"{count:,}", msg)

            console.print(error_table)
        elif stats.valid_entries_count > 0:
            console.print(Panel("[green][OK] No ERROR or CRITICAL entries detected in analyzed logs.[/green]", box=box.ROUNDED))

        # 4. Sample Malformed Entries
        if stats.sample_malformed_entries:
            mal_table = Table(box=box.ROUNDED, title="Sample Malformed / Corrupted Log Lines")
            mal_table.add_column("Line #", justify="right", width=8, style="yellow")
            mal_table.add_column("Parsing Issue", width=32, style="red")
            mal_table.add_column("Raw Line Preview", style="dim")

            for item in stats.sample_malformed_entries[:5]:
                preview = item["raw_line"][:80] + ("..." if len(item["raw_line"]) > 80 else "")
                mal_table.add_row(str(item["line_number"]), item["reason"], preview)

            console.print(mal_table)

        # 5. AI Troubleshooting Insights
        if stats.ai_insights:
            ai_data = stats.ai_insights
            ai_content = ""
            if "analysis" in ai_data:
                ai_content = ai_data["analysis"]
            elif "findings" in ai_data:
                parts = []
                for item in ai_data["findings"]:
                    parts.append(f"[bold red]* Error:[/bold red] {item['error']} ([bold]{item['occurrence_count']} occurrences[/bold])")
                    parts.append(f"  [bold yellow]Possible Cause:[/bold yellow] {item['probable_cause']}")
                    parts.append("  [bold green]Recommended Actions:[/bold green]")
                    for step in item["troubleshooting_steps"]:
                        parts.append(f"    - {step}")
                    parts.append("")
                ai_content = "\n".join(parts)
                if "ollama_setup_guide" in ai_data:
                    ai_content += f"\n[dim]{ai_data['ollama_setup_guide']}[/dim]"

            source_label = ai_data.get("source", "AI Engine")
            console.print(Panel(ai_content, title=f"[bold magenta][AI Diagnostics] ({source_label})[/bold magenta]", box=box.ROUNDED))

        # 6. Sample Filtered Entries (if requested)
        if top_entries:
            entries_table = Table(box=box.ROUNDED, title=f"Filtered Log Entries Preview (Showing {len(top_entries)})")
            entries_table.add_column("Line", justify="right", width=6, style="dim")
            entries_table.add_column("Timestamp", width=20, style="cyan")
            entries_table.add_column("Level", width=10)
            entries_table.add_column("Message", style="white")

            for entry in top_entries:
                color = LEVEL_STYLES.get(entry.level, "white")
                ts_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "N/A"
                entries_table.add_row(
                    str(entry.line_number),
                    ts_str,
                    f"[{color}]{entry.level}[/{color}]",
                    entry.message.split("\n", 1)[0][:100]
                )
            console.print(entries_table)

    def _print_plain_report(
        self,
        stats: AnalysisStats,
        file_path: str,
        filter_criteria: Optional[FilterCriteria] = None,
        top_entries: Optional[List[LogEntry]] = None,
    ) -> None:
        """Fallback plain-text console report without external formatting dependencies."""
        print("=" * 72)
        print("                 LOG FILE ANALYSIS & DIAGNOSTICS REPORT")
        print("=" * 72)
        print(f"Log File Path:            {file_path}")
        print(f"Total Lines Scanned:      {stats.total_lines_read:,}")
        print(f"Valid Log Entries:        {stats.valid_entries_count:,}")
        print(f"Malformed / Corrupt:      {stats.malformed_entries_count:,}")
        if filter_criteria and filter_criteria.is_active():
            print(f"Filtered Matched:         {stats.filtered_entries_count:,}")
        if stats.earliest_timestamp and stats.latest_timestamp:
            print(f"Time Window:              {stats.earliest_timestamp} -> {stats.latest_timestamp}")
        print(f"Error Rate:               {stats.error_rate}%")
        print("-" * 72)
        print("LOG LEVEL DISTRIBUTION:")
        for lvl, count in sorted(stats.level_counts.items()):
            print(f"  {lvl:<12} : {count:>8,}")
        print("-" * 72)
        if stats.top_errors:
            print("TOP ERROR MESSAGES:")
            for rank, (msg, count) in enumerate(stats.top_errors, start=1):
                print(f"  [{rank}] {count:,} occurrences: {msg}")
            print("-" * 72)
        if stats.sample_malformed_entries:
            print("SAMPLE MALFORMED LINES:")
            for item in stats.sample_malformed_entries[:5]:
                print(f"  Line {item['line_number']}: {item['reason']} -> {item['raw_line'][:60]}")
            print("-" * 72)
        if stats.ai_insights:
            print("AI DIAGNOSTIC INSIGHTS:")
            print(json.dumps(stats.ai_insights, indent=2))
            print("=" * 72)


class JsonReporter:
    """Exports structured analysis reports to JSON format."""

    @staticmethod
    def generate_report_dict(
        stats: AnalysisStats,
        file_path: str,
        filter_criteria: Optional[FilterCriteria] = None,
        entries: Optional[List[LogEntry]] = None,
    ) -> Dict[str, Any]:
        """Build the full dictionary structure for JSON export."""
        report = stats.to_dict()
        report["metadata"] = {
            "file_path": str(file_path),
            "filters_applied": filter_criteria.to_dict() if filter_criteria else None,
        }
        if entries is not None:
            report["entries"] = [e.to_dict() for e in entries]
        return report

    @classmethod
    def to_json_string(
        cls,
        stats: AnalysisStats,
        file_path: str,
        filter_criteria: Optional[FilterCriteria] = None,
        entries: Optional[List[LogEntry]] = None,
        indent: int = 2,
    ) -> str:
        """Convert analysis report into formatted JSON string."""
        data = cls.generate_report_dict(stats, file_path, filter_criteria, entries)
        return json.dumps(data, indent=indent, default=str)

    @classmethod
    def save_to_file(
        cls,
        stats: AnalysisStats,
        file_path: str,
        output_path: str,
        filter_criteria: Optional[FilterCriteria] = None,
        entries: Optional[List[LogEntry]] = None,
    ) -> None:
        """Save analysis report to a JSON file on disk."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        json_content = cls.to_json_string(stats, file_path, filter_criteria, entries)
        with open(target, "w", encoding="utf-8") as f:
            f.write(json_content)
        logger.info("JSON report saved to %s", target)
