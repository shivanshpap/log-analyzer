"""End-to-end integration tests for the log_analyzer CLI tool."""

import json
import subprocess
import sys
from pathlib import Path
import pytest

SAMPLE_LOG = Path(__file__).parent.parent / "samples" / "sample_application.log"


class TestCLIIntegration:
    """Test running log_analyzer.py via command line subprocess."""

    def run_cli(self, args: list) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "log_analyzer.py"] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )

    def test_cli_basic_run(self):
        res = self.run_cli([str(SAMPLE_LOG)])
        assert res.returncode == 0
        assert "LOG FILE ANALYSIS & DIAGNOSTICS REPORT" in res.stdout or "Summary Overview" in res.stdout
        assert "Total Lines Scanned" in res.stdout

    def test_cli_level_filter_error(self):
        # python log_analyzer.py application.log --level ERROR
        res = self.run_cli([str(SAMPLE_LOG), "--level", "ERROR"])
        assert res.returncode == 0
        assert "ERROR" in res.stdout

    def test_cli_keyword_filter(self):
        res = self.run_cli([str(SAMPLE_LOG), "--keyword", "timeout"])
        assert res.returncode == 0

    def test_cli_json_output(self):
        res = self.run_cli([str(SAMPLE_LOG), "--json"])
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert "summary" in data
        assert "level_distribution" in data
        assert data["summary"]["total_lines_read"] > 0

    def test_cli_output_file(self, tmp_path):
        out_file = tmp_path / "cli_report.json"
        res = self.run_cli([str(SAMPLE_LOG), "-o", str(out_file)])
        assert res.returncode == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["summary"]["valid_entries_count"] > 0

    def test_cli_ai_mock(self):
        res = self.run_cli([str(SAMPLE_LOG), "--mock-ai"])
        assert res.returncode == 0
        assert "AI Diagnostic" in res.stdout or "Mock AI Error Analysis" in res.stdout

    def test_cli_nonexistent_file(self):
        res = self.run_cli(["nonexistent_file_xyz.log"])
        assert res.returncode != 0
        assert "does not exist" in res.stderr
