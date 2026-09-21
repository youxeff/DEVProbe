"""Executed in a fresh child, never as a preexec_fn in threaded FastAPI."""

import os
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
# Node reserves large virtual address space; enforce resident memory at container level.
if os.environ.get("DEVPROBE_LIMIT_ADDRESS_SPACE") == "1":
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024,) * 2)
os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
