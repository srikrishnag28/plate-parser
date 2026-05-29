import subprocess
import tempfile
import json
import os
import logging
import sys

logger = logging.getLogger(__name__)

SANDBOX_TIMEOUT = 30  # seconds


def run_parser_in_sandbox(parser_code: str, csv_content: str) -> dict:
    """
    Execute a generated parser script against CSV content in an isolated subprocess.

    The parser receives the CSV file path as argv[1] and must print a single JSON
    object to stdout. stderr is captured and included in error messages.
    Raises RuntimeError on timeout, non-zero exit, empty output, or invalid JSON.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        parser_path = os.path.join(tmpdir, "parser.py")
        csv_path = os.path.join(tmpdir, "input.csv")

        with open(parser_path, "w", encoding="utf-8") as f:
            f.write(parser_code)

        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        try:
            result = subprocess.run(
                [sys.executable, parser_path, csv_path],
                capture_output=True,
                text=True,
                timeout=SANDBOX_TIMEOUT,
                cwd=tmpdir,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONPATH": "",
                },
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Parser timed out after {SANDBOX_TIMEOUT}s")
        except Exception as e:
            raise RuntimeError(f"Sandbox execution error: {e}")

        if result.returncode != 0:
            stderr = result.stderr[:1000]
            raise RuntimeError(f"Parser failed (exit {result.returncode}): {stderr}")

        stdout = result.stdout.strip()
        if not stdout:
            raise RuntimeError("Parser produced no output")

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Parser output is not valid JSON: {e}")
