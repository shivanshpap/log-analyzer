"""AI-powered error analysis and troubleshooting suggestions using Ollama or heuristic fallback."""

import logging
import json
from typing import Dict, Any, List, Tuple, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("LogAnalyzer.AIAdvisor")

# Built-in heuristic knowledge base for common application failure patterns
COMMON_ERROR_PATTERNS = [
    {
        "pattern": r"(?i)(connection refused|connectex|failed to connect|econnrefused)",
        "cause": "Service unreachable or network port blocked.",
        "troubleshooting": [
            "Verify the target service process is active and listening on the designated port (e.g. `netstat -ano` or `lsof -i`).",
            "Check firewall rules, security groups, and DNS name resolution.",
            "Verify connection string host, port, and network route."
        ]
    },
    {
        "pattern": r"(?i)(timeout|timed out|read timed out|etimedout)",
        "cause": "Request exceeded timeout deadline due to slow queries, high load, or network latency.",
        "troubleshooting": [
            "Check server CPU, memory, and database lock contention.",
            "Review query execution plans and add missing database indices.",
            "Increase timeout threshold or implement async queue processing."
        ]
    },
    {
        "pattern": r"(?i)(out of memory|oom|heap space|memoryerror)",
        "cause": "Process exhausted available memory allocation.",
        "troubleshooting": [
            "Inspect memory profiling / heap dump for leaks or unbounded collections.",
            "Increase max heap size (-Xmx) or container memory limits.",
            "Ensure batching or streaming is used for large data processing."
        ]
    },
    {
        "pattern": r"(?i)(unauthorized|401|forbidden|403|access denied|invalid token|expired)",
        "cause": "Authentication failure, expired session token, or insufficient permissions.",
        "troubleshooting": [
            "Verify API credentials, tokens, and secret rotation schedules.",
            "Check IAM role policies or user privilege grants.",
            "Ensure clock synchronization (NTP) to avoid token validation skew."
        ]
    },
    {
        "pattern": r"(?i)(nullpointerexception|attributeerror|typeerror|undefined)",
        "cause": "Code attempted to access property or method on null/None object.",
        "troubleshooting": [
            "Inspect stack trace line numbers to locate the uninitialized reference.",
            "Add null-check guards or optional chaining.",
            "Verify API response schemas when parsing external payloads."
        ]
    },
    {
        "pattern": r"(?i)(filenotfoundexception|no such file|file does not exist)",
        "cause": "Referenced file or directory path does not exist or has bad permissions.",
        "troubleshooting": [
            "Verify absolute vs relative working directory paths.",
            "Check file existence and read permissions for the application user.",
            "Verify Docker volume mounts or deployment bundle contents."
        ]
    },
    {
        "pattern": r"(?i)(ssl|certificate|cert_verify|handshake_failure)",
        "cause": "TLS/SSL certificate expired, untrusted CA, or cipher mismatch.",
        "troubleshooting": [
            "Verify the server certificate expiration date.",
            "Ensure root CA bundle is up-to-date in system trust store.",
            "Check domain name matches the certificate SAN (Subject Alternative Name)."
        ]
    },
    {
        "pattern": r"(?i)(too many requests|429|rate limit)",
        "cause": "API rate limit or concurrency quota exceeded.",
        "troubleshooting": [
            "Implement exponential backoff with jitter on request retries.",
            "Introduce client-side rate limiting or caching.",
            "Request quota tier upgrade from upstream provider."
        ]
    },
]


class AIAdvisor:
    """Provides root cause analysis and troubleshooting recommendations for detected log errors."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3:latest",
        timeout_seconds: int = 15,
        mock_mode: bool = False,
    ) -> None:
        """
        Initialize the AI Advisor.

        Args:
            ollama_url: Base URL for local Ollama REST API.
            model: Ollama model identifier (e.g. 'llama3:latest', 'mistral', 'deepseek-r1').
            timeout_seconds: Request timeout in seconds.
            mock_mode: If True, uses simulated AI responses without making network calls.
        """
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.mock_mode = mock_mode

    def is_ollama_available(self) -> bool:
        """Check if Ollama service is reachable and responsive."""
        if self.mock_mode:
            return True
        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/tags",
                headers={"User-Agent": "LogAnalyzer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.debug("Ollama availability check failed: %s", exc)
            return False

    def generate_heuristic_advice(self, top_errors: List[Tuple[str, int]]) -> Dict[str, Any]:
        """Generate deterministic troubleshooting guidance based on curated heuristic patterns."""
        import re

        recommendations = []
        for error_msg, count in top_errors:
            matched = False
            for pattern_info in COMMON_ERROR_PATTERNS:
                if re.search(pattern_info["pattern"], error_msg):
                    recommendations.append({
                        "error": error_msg,
                        "occurrence_count": count,
                        "probable_cause": pattern_info["cause"],
                        "troubleshooting_steps": pattern_info["troubleshooting"],
                    })
                    matched = True
                    break

            if not matched:
                recommendations.append({
                    "error": error_msg,
                    "occurrence_count": count,
                    "probable_cause": "Unclassified application error. Potential runtime exception or unexpected input.",
                    "troubleshooting_steps": [
                        "Examine preceding DEBUG/INFO logs for transaction context.",
                        "Inspect full stack trace and source code around the reported error.",
                        "Check system telemetry (CPU, RAM, I/O) at the time of the error."
                    ],
                })

        return {
            "source": "Heuristic Expert Engine (Ollama offline or not configured)",
            "model": "rule-based-advisor-v1",
            "findings": recommendations,
            "ollama_setup_guide": (
                "To enable live generative LLM analysis:\n"
                "1. Download & start Ollama: https://ollama.ai\n"
                "2. Run model: `ollama run llama3`\n"
                "3. Re-run log_analyzer with `--ai`"
            )
        }

    def analyze_errors(
        self, top_errors: List[Tuple[str, int]], total_entries: int
    ) -> Dict[str, Any]:
        """
        Analyze detected errors using Ollama if available, falling back to heuristic advice.

        Args:
            top_errors: List of (error_message, count) tuples.
            total_entries: Total log entries scanned.

        Returns:
            Dictionary containing causes, troubleshooting suggestions, and metadata.
        """
        if not top_errors:
            return {
                "source": "None",
                "message": "No errors detected in analyzed log entries."
            }

        if self.mock_mode:
            return {
                "source": "Ollama (Mock Mode)",
                "model": self.model,
                "analysis": (
                    "### Mock AI Error Analysis\n\n"
                    "**1. Root Cause Summary:**\n"
                    "The detected errors indicate intermittent downstream network timeouts and authentication failures.\n\n"
                    "**2. Recommended Actions:**\n"
                    "- Review downstream connection pool settings.\n"
                    "- Check API authorization token validity and expiration intervals.\n"
                    "- Verify health of database replicas."
                ),
            }

        # Check if Ollama is running
        if not self.is_ollama_available():
            logger.info("Ollama is not reachable at %s. Using heuristic analysis.", self.ollama_url)
            return self.generate_heuristic_advice(top_errors)

        # Prepare prompt for Ollama
        errors_summary = "\n".join(
            f"- [{count} occurrences] {msg}" for msg, count in top_errors
        )

        prompt = (
            "You are an expert site reliability and software engineer.\n"
            "An application log file was analyzed with the following top detected error patterns:\n\n"
            f"{errors_summary}\n\n"
            f"Total log entries processed: {total_entries}.\n\n"
            "Please provide a structured, concise diagnosis with:\n"
            "1. Most Probable Root Cause for each error pattern.\n"
            "2. Specific, actionable troubleshooting steps to resolve them.\n"
            "3. Preventative recommendations to avoid future occurrences.\n"
            "Keep the response practical, direct, and formatted in clean markdown."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "LogAnalyzer/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "").strip()
                return {
                    "source": "Ollama LLM",
                    "model": self.model,
                    "analysis": response_text,
                }
        except Exception as exc:
            logger.warning("Error querying Ollama API: %s. Falling back to heuristic.", exc)
            fallback = self.generate_heuristic_advice(top_errors)
            fallback["ollama_error"] = str(exc)
            return fallback
