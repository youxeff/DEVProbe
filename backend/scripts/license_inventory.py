"""Generate an inventory from installed package metadata and committed npm locks.

This records declarations; it is not a legal approval or a complete container SBOM.
"""

import importlib.metadata as metadata
import json
import subprocess
import sys
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]


def python_inventory(requirements):
    rows = []
    pending = [
        Requirement(line)
        for line in requirements.read_text().splitlines()
        if line and not line.startswith(("#", "-"))
    ]
    visited = set()
    while pending:
        requirement = pending.pop()
        key = (requirement.name.lower(), tuple(sorted(requirement.extras)))
        if key in visited:
            continue
        visited.add(key)
        dist = metadata.distribution(requirement.name)
        meta = dist.metadata
        declared = meta.get("License-Expression") or meta.get("License") or ""
        if not declared or len(declared) > 120:
            declared = "; ".join(
                value.removeprefix("License :: ")
                for value in meta.get_all("Classifier", [])
                if value.startswith("License ::")
            )
        rows.append(
            {
                "name": meta["Name"],
                "version": dist.version,
                "declared_license": declared or "UNDECLARED — review required",
            }
        )
        for dependency in dist.requires or []:
            parsed = Requirement(dependency)
            if parsed.marker is None or any(
                parsed.marker.evaluate({"extra": extra}) for extra in {"", *requirement.extras}
            ):
                pending.append(parsed)
    return sorted({row["name"]: row for row in rows}.values(), key=lambda row: row["name"].lower())


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--tools":
        print(json.dumps(python_inventory(ROOT / "backend/tools/requirements.txt")))
        return
    result = {
        "note": (
            "Declared package licenses only. Review source notices, hosted service terms, "
            "and final image SBOM before release."
        ),
        "backend_python_packages": python_inventory(ROOT / "backend/requirements.txt"),
    }
    tool_python = ROOT / "backend/tools/.venv/bin/python"
    if tool_python.exists():
        result["analysis_python_tools"] = json.loads(
            subprocess.check_output([str(tool_python), __file__, "--tools"])
        )
    for folder in ("frontend", "backend/tools"):
        lock = json.loads((ROOT / folder / "package-lock.json").read_text())
        result[folder + "_npm_packages"] = [
            {
                "path": path,
                "version": row.get("version"),
                "declared_license": row.get("license", "UNDECLARED — review required"),
                "development_only": bool(row.get("dev")),
            }
            for path, row in lock["packages"].items()
            if path
        ]
    (ROOT / "docs/dependency-licenses.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Wrote docs/dependency-licenses.json")


if __name__ == "__main__":
    main()
