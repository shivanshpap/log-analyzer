"""Unit tests for the AIAdvisor module (heuristics, Ollama offline fallback, mock mode)."""

import pytest
from src.ai_advisor import AIAdvisor


class TestAIAdvisor:
    """Test suite for AI troubleshooting suggestions."""

    def test_mock_mode_response(self):
        advisor = AIAdvisor(mock_mode=True)
        assert advisor.is_ollama_available() is True

        top_errors = [("Connection refused: host=db:5432", 10)]
        result = advisor.analyze_errors(top_errors, total_entries=100)

        assert result["source"] == "Ollama (Mock Mode)"
        assert "Mock AI Error Analysis" in result["analysis"]

    def test_heuristic_pattern_recognition(self):
        advisor = AIAdvisor(mock_mode=False)

        errors = [
            ("Connection refused to postgres-db:5432", 5),
            ("Read timed out waiting for payment response", 3),
            ("Fatal: Out of memory (Heap exhausted)", 2),
            ("Unauthorized: 401 JWT signature expired", 4),
            ("AttributeError: 'NoneType' object has no attribute 'id'", 1),
            ("FileNotFoundException: config/app.yml not found", 1),
            ("SSL certificate verify failed: certificate has expired", 1),
            ("429 Too Many Requests: Rate limit exceeded", 2),
        ]

        advice = advisor.generate_heuristic_advice(errors)
        findings = advice["findings"]
        assert len(findings) == 8

        # Check that specific actionable troubleshooting steps were produced
        for item in findings:
            assert len(item["troubleshooting_steps"]) > 0
            assert len(item["probable_cause"]) > 0

    def test_empty_errors_list(self):
        advisor = AIAdvisor()
        result = advisor.analyze_errors([], total_entries=50)
        assert "No errors detected" in result["message"]

    def test_offline_ollama_fallback(self):
        # Point to an invalid unreachable port to guarantee offline trigger
        advisor = AIAdvisor(ollama_url="http://127.0.0.1:59999", timeout_seconds=1)
        assert advisor.is_ollama_available() is False

        result = advisor.analyze_errors([("Connection refused: host=redis", 3)], total_entries=20)
        assert "Heuristic" in result["source"]
        assert "findings" in result
