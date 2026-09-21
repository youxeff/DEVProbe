"""Bounded, secret-free subprocesses. Only trusted installed tools are invoked."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryFile


class AnalyzerError(Exception):
    """A safe diagnostic code; never include raw tool stderr/source."""


def run_json(command: list[str], workspace: Path, *, timeout: float = 40, codes=(0, 1)):
    env = {
        "PATH": f"{Path(sys.executable).parent}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(workspace),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": str(workspace),
        "PYTHONNOUSERSITE": "1",
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SETTINGS_FILE": str(workspace / "semgrep-settings.yml"),
        "RADONFILESENCODING": "UTF-8",
        "NODE_OPTIONS": "--max-old-space-size=512",
    }
    wrapped = [sys.executable, "-I", str(Path(__file__).with_name("process_limits.py")), *command]
    with TemporaryFile(dir=workspace) as stdout, TemporaryFile(dir=workspace) as stderr:
        try:
            process = subprocess.Popen(
                wrapped,
                cwd=workspace,
                env=env,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise AnalyzerError("execution timed out") from None
            if process.returncode not in codes:
                raise AnalyzerError("tool execution failed")
            stdout.seek(0)
            output = stdout.read(8 * 1024 * 1024 + 1)
            if len(output) > 8 * 1024 * 1024:
                raise AnalyzerError("output limit exceeded")
            return json.loads(output)
        except (OSError, ValueError):
            raise AnalyzerError("tool unavailable or invalid output") from None
