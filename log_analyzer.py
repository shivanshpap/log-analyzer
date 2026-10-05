#!/usr/bin/env python3
"""
Log Analyzer CLI Tool
A robust, streaming Python CLI tool that parses application logs, analyzes patterns,
applies multi-attribute filtering, calculates error frequency statistics, and
provides automated AI-powered troubleshooting advice.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from src.parser import LogParser
from src.filter import LogFilter
from src.analyzer import LogAnalyzer
from src.reporter import ConsoleReporter, JsonReporter
from src.ai_advisor import AIAdvisor


def setup_tool_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure Python's standard logging for the CLI application."""
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="log_analyzer",
        description="Reads an application log file, analyzes entries, and generates summary reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python log_analyzer.py application.log
  python log_analyzer.py application.log --level ERROR
  python log_analyzer.py application.log --level WARNING,ERROR --keyword "timeout"
  python log_analyzer.py application.log --start-time "2026-09-30 12:00:00" --end-time "2026-09-30 18:00:00"
  python log_analyzer.py application.log --level ERROR --json
  python log_analyzer.py application.log --output report.json
  python log_analyzer.py application.log --ai
  python log_analyzer.py application.log --level ERROR --ai --ai-model llama3
        """,
    )

    # Positional: Log file path
    parser.add_argument(
        "log_file",
        type=str,
        help="Path to the application log file to analyze.",
    )

    # Filtering arguments
    filter_group = parser.add_argument_group("Filtering Options")
    filter_group.add_argument(
        "--level",
        "-l",
        type=str,
        default=None,
        help="Filter by log level (e.g. ERROR, WARNING, INFO or comma-separated: ERROR,CRITICAL).",
    )
    filter_group.add_argument(
        "--keyword",
        "-k",
        type=str,
        default=None,
        help="Filter entries containing this keyword in the message or logger name.",
    )
    filter_group.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Perform case-sensitive keyword matching (default is case-insensitive).",
    )
    filter_group.add_argument(
        "--start-time",
        "--from",
        type=str,
        default=None,
        dest="start_time",
        help="Filter entries with timestamp on or after this date/time (e.g. '2026-09-30 14:00:00').",
    )
    filter_group.add_argument(
        "--end-time",
        "--to",
        type=str,
        default=None,
        dest="end_time",
        help="Filter entries with timestamp on or before this date/time.",
    )

    # Analysis & Parsing options
    analysis_group = parser.add_argument_group("Analysis & Parsing Options")
    analysis_group.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of most frequent error messages to display (default: 5).",
    )
    analysis_group.add_argument(
        "--pattern",
        type=str,
        default=None,
        help="Custom regular expression pattern with named groups (?P<timestamp>...), (?P<level>...), (?P<message>...).",
    )
    analysis_group.add_argument(
        "--no-multiline",
        action="store_true",
        help="Disable combining multiline exception stack traces with the preceding log entry.",
    )
    analysis_group.add_argument(
        "--no-normalize",
        action="store_true",
        help="Disable grouping of similar errors with dynamic values (IDs, IPs, UUIDs).",
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format to stdout.",
    )
    output_group.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Save complete analysis report as JSON to the specified file path.",
    )
    output_group.add_argument(
        "--show-entries",
        "--list",
        action="store_true",
        dest="show_entries",
        help="Display preview of filtered log entries in the console.",
    )
    output_group.add_argument(
        "--max-entries",
        type=int,
        default=15,
        help="Maximum number of filtered entries to preview (default: 15).",
    )

    # AI Extension options
    ai_group = parser.add_argument_group("AI Troubleshooting Options")
    ai_group.add_argument(
        "--ai",
        "--ai-analyze",
        action="store_true",
        dest="ai_analyze",
        help="Use Ollama or heuristic engine to analyze detected errors and suggest fixes.",
    )
    ai_group.add_argument(
        "--ai-model",
        type=str,
        default="llama3:latest",
        help="Ollama model identifier to use for diagnostics (default: 'llama3:latest').",
    )
    ai_group.add_argument(
        "--ai-url",
        type=str,
        default="http://localhost:11434",
        help="Base URL for the Ollama API (default: 'http://localhost:11434').",
    )
    ai_group.add_argument(
        "--mock-ai",
        action="store_true",
        help="Run AI analysis in mock mode for testing without requiring a live Ollama server.",
    )

    # Operational verbosity
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed diagnostic logging output.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all informational logging output.",
    )

    return parser


def main() -> int:
    """Main CLI entry point."""
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = build_arg_parser()
    args = parser.parse_args()

    setup_tool_logging(verbose=args.verbose, quiet=args.quiet)

    log_path = Path(args.log_file)
    if not log_path.exists():
        print(f"Error: Log file '{args.log_file}' does not exist.", file=sys.stderr)
        return 1
    if not log_path.is_file():
        print(f"Error: '{args.log_file}' is not a regular file.", file=sys.stderr)
        return 1

    try:
        # 1. Initialize Log Filter
        log_filter = LogFilter.create(
            levels=args.level,
            keyword=args.keyword,
            case_sensitive=args.case_sensitive,
            start_time=args.start_time,
            end_time=args.end_time,
        )

        # 2. Initialize Parser
        log_parser = LogParser(
            custom_pattern=args.pattern,
            combine_multiline=not args.no_multiline,
        )

        # 3. Stream and Analyze Log File
        analyzer = LogAnalyzer(
            top_n_errors=args.top_n,
            normalize_errors=not args.no_normalize,
        )

        collect_entries = args.show_entries or (args.json and log_filter.criteria.is_active()) or (args.output is not None)
        entry_stream = log_parser.parse_file(log_path)
        stats, matched_entries = analyzer.analyze(
            entry_stream,
            log_filter=log_filter,
            collect_filtered_entries=collect_entries,
        )

        # 4. Optional AI Analysis
        if args.ai_analyze or args.mock_ai:
            advisor = AIAdvisor(
                ollama_url=args.ai_url,
                model=args.ai_model,
                mock_mode=args.mock_ai,
            )
            stats.ai_insights = advisor.analyze_errors(
                top_errors=stats.top_errors,
                total_entries=stats.filtered_entries_count or stats.valid_entries_count,
            )

        # 5. Output Results
        if args.json:
            preview_entries = matched_entries if collect_entries else None
            print(JsonReporter.to_json_string(
                stats=stats,
                file_path=str(log_path),
                filter_criteria=log_filter.criteria,
                entries=preview_entries,
            ))
        else:
            reporter = ConsoleReporter()
            preview = matched_entries[:args.max_entries] if args.show_entries else None
            reporter.print_report(
                stats=stats,
                file_path=str(log_path),
                filter_criteria=log_filter.criteria,
                top_entries=preview,
            )

        # 6. Save JSON report to file if requested
        if args.output:
            JsonReporter.save_to_file(
                stats=stats,
                file_path=str(log_path),
                output_path=args.output,
                filter_criteria=log_filter.criteria,
                entries=matched_entries,
            )
            if not args.json and not args.quiet:
                print(f"\nReport successfully exported to {args.output}")

        return 0

    except Exception as exc:
        logging.exception("Fatal error during log analysis: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
