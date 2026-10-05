# 📊 Log Analyzer CLI

A high-performance, modular Python CLI tool designed to ingest, parse, filter, and analyze application log files of any scale. It calculates detailed metrics and level distributions, detects recurring error patterns, handles malformed lines safely, and features an **AI-powered troubleshooting assistant** (powered by Ollama with an intelligent offline heuristic fallback engine).

---

## 🚀 Key Features

* **Robust Regex Log Parsing**:
  * Auto-detects standard Python logging, ISO-8601 timestamps, bracketed formats, and custom regex (`--pattern`).
  * Seamlessly aggregates multiline exception stack traces (e.g. Python tracebacks).
  * Safely catches and logs malformed/corrupted lines without terminating execution.
* **Streaming & Low-Memory Performance**:
  * Utilizes Python generators (`yield LogEntry`) for a single-pass streaming architecture.
  * Capable of parsing and analyzing **100,000+ log lines in ~1.3 seconds** with constant $O(1)$ memory overhead.
* **Multi-Attribute Filtering**:
  * Filter by **Log Level**: `--level ERROR` or comma-separated `--level WARNING,ERROR,CRITICAL`.
  * Filter by **Keyword**: `--keyword "database"` with optional `--case-sensitive`.
  * Filter by **Date/Time Range**: `--start-time "2026-09-30 10:00:00"` and `--end-time "2026-09-30 14:00:00"`.
* **Statistical Analysis & Pattern Normalization**:
  * Counts total entries, valid lines, malformed lines, and log level breakdown (`INFO`, `WARNING`, `ERROR`, `CRITICAL`, `DEBUG`).
  * Normalizes dynamic tokens (UUIDs, IP addresses, IDs, hex values) to aggregate similar error occurrences into ranked frequency patterns.
  * Calculates log timeline spans (start, end, duration) and error rates.
* **Flexible Reporting**:
  * **Interactive Console Dashboard**: Formatted with Rich tables, colored badges, visual distribution bars, and malformed line previews.
  * **Machine-Readable JSON**: Complete structured JSON output to stdout (`--json`) or saved to disk (`-o report.json`).
* **🤖 AI Troubleshooting Extension**:
  * Connects to local [Ollama](https://ollama.ai) models (e.g. `llama3`, `mistral`) via `--ai` to diagnose root causes and suggest actionable remediation steps.
  * **Built-in Offline Heuristic Fallback**: If Ollama is offline or not installed, automatically activates a deterministic expert rule engine for common infrastructure failures (connection refused, timeouts, OOM, auth issues, rate limits, etc.).

---

## 📁 Project Architecture

```
Analyzer/
├── log_analyzer.py             # CLI entrypoint executable
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Build & pytest configuration
├── src/
│   ├── __init__.py             # Package exports
│   ├── models.py               # LogEntry, FilterCriteria, and AnalysisStats dataclasses
│   ├── parser.py               # Regex-based streaming log parser & multiline handler
│   ├── filter.py               # Multi-attribute filter engine (level, keyword, time)
│   ├── analyzer.py             # Streaming statistical aggregator & error normalizer
│   ├── reporter.py             # ConsoleReporter (Rich & plain text) & JsonReporter
│   └── ai_advisor.py           # Ollama client & heuristic troubleshooting engine
├── tests/
│   ├── test_parser.py          # Parser unit tests (formats, tracebacks, corrupt lines)
│   ├── test_filter.py          # Filter unit tests (levels, keywords, date ranges)
│   ├── test_analyzer.py        # Statistics, error ranking, and normalization tests
│   ├── test_reporter.py        # JSON & Console report validation tests
│   ├── test_ai_advisor.py      # Heuristics, mock mode, and offline fallback tests
│   └── test_cli.py             # Subprocess CLI integration tests
└── samples/
    ├── sample_application.log  # Realistic application log with traces & errors
    └── generate_sample_logs.py # Synthetic log generator utility (for 100k+ lines)
```

---

## 🛠️ Installation & Setup

### Prerequisites
* Python 3.8 or higher

### Install Dependencies
```bash
python -m pip install -r requirements.txt
```

---

## 💻 CLI Usage Guide

### 1. Basic Analysis
Scan and analyze a log file, generating a terminal summary report:
```bash
python log_analyzer.py samples/sample_application.log
```

### 2. Filter by Log Level
Isolate errors and critical issues (as requested in the objective):
```bash
python log_analyzer.py samples/sample_application.log --level ERROR
```
Or multiple levels:
```bash
python log_analyzer.py samples/sample_application.log --level WARNING,ERROR,CRITICAL
```

### 3. Filter by Keyword
Search for log entries containing specific keywords (e.g. "timeout", "pool", "auth"):
```bash
python log_analyzer.py samples/sample_application.log --keyword "timeout"
```
To inspect matching log lines in the terminal:
```bash
python log_analyzer.py samples/sample_application.log --keyword "timeout" --show-entries
```

### 4. Filter by Date & Time Window
Analyze logs within a specific time window:
```bash
python log_analyzer.py samples/sample_application.log --start-time "2026-09-30 10:05:00" --end-time "2026-09-30 10:10:00" --show-entries
```

### 5. Export JSON Reports
Output JSON to stdout:
```bash
python log_analyzer.py samples/sample_application.log --json
```
Save the report directly to a file:
```bash
python log_analyzer.py samples/sample_application.log -o analysis_report.json
```

### 6. AI-Powered Troubleshooting Assistance
Activate the AI diagnostic engine:
```bash
python log_analyzer.py samples/sample_application.log --ai
```
*(Optional) Specify a custom Ollama model or host:*
```bash
python log_analyzer.py samples/sample_application.log --ai --ai-model llama3 --ai-url http://localhost:11434
```
*(Optional) Run in mock AI mode without a local Ollama server:*
```bash
python log_analyzer.py samples/sample_application.log --mock-ai
```

---

## 📋 Command Line Options Reference

| Argument | Description | Default |
| :--- | :--- | :--- |
| `log_file` | Path to the application log file to analyze | *Required* |
| `--level`, `-l` | Filter by log level (e.g. `ERROR` or `WARNING,ERROR`) | `None` |
| `--keyword`, `-k` | Filter by substring in message or logger | `None` |
| `--case-sensitive` | Case-sensitive keyword matching | `False` |
| `--start-time`, `--from` | Lower time boundary (e.g. `'2026-09-30 10:00:00'`) | `None` |
| `--end-time`, `--to` | Upper time boundary (e.g. `'2026-09-30 12:00:00'`) | `None` |
| `--top-n` | Number of top error messages to rank | `5` |
| `--pattern` | Custom regex pattern with named capture groups | Auto |
| `--no-multiline` | Disable combining multiline stack traces | `False` |
| `--no-normalize` | Disable masking dynamic IDs/UUIDs/IPs in errors | `False` |
| `--json` | Print structured report as JSON to stdout | `False` |
| `--output`, `-o` | Save JSON report to specified file path | `None` |
| `--show-entries`, `--list` | Display preview of matched entries in terminal | `False` |
| `--max-entries` | Max entries to show in preview | `15` |
| `--ai`, `--ai-analyze` | Run AI root-cause analysis and troubleshooting | `False` |
| `--ai-model` | Ollama model identifier | `llama3:latest` |
| `--ai-url` | Ollama REST API endpoint | `http://localhost:11434` |
| `--mock-ai` | Simulated AI response mode for testing | `False` |
| `-v`, `--verbose` | Enable debug logging | `False` |
| `-q`, `--quiet` | Suppress non-error output | `False` |

---

## ⚡ Performance Benchmark

A generator script is provided in `samples/generate_sample_logs.py` to test high-throughput processing:
```bash
# Generate 100,000 realistic log lines (~9 MB)
python samples/generate_sample_logs.py --lines 100000 --output samples/large_sample.log

# Run analysis and benchmark
python log_analyzer.py samples/large_sample.log -o report_large.json
```
**Results on Windows (Python 3.13):**
* **100,000 log lines** scanned, parsed, aggregated, and exported to JSON in **1.37 seconds** (~73,000 lines/sec).

---

## 🧪 Running Unit Tests

The test suite contains **36 unit and integration tests** covering parsing, normalization, filtering, statistics, JSON output, console rendering, AI troubleshooting, and CLI subprocess execution.

Run the test suite with `pytest`:
```bash
python -m pytest -v
```

---

## 📄 License
MIT License. Created for the Application Log Analyzer assignment.
