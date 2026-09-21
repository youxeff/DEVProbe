def analyze_changed_files(files):
    issues = []

    total_files = len(files)
    total_changes = sum(file.get("changes", 0) for file in files)

    if total_files > 15:
        issues.append({
            "file_path": "PR-level",
            "line_number": None,
            "tool": "devprobe-basic",
            "category": "maintainability",
            "severity": "medium",
            "message": "Large pull request detected.",
            "recommendation": "Consider splitting this PR into smaller, easier-to-review changes."
        })

    if total_changes > 500:
        issues.append({
            "file_path": "PR-level",
            "line_number": None,
            "tool": "devprobe-basic",
            "category": "maintainability",
            "severity": "medium",
            "message": "Large number of changed lines detected.",
            "recommendation": "Large PRs are harder to review. Consider breaking this work into smaller PRs."
        })

    has_code_change = False
    has_test_change = False

    for file in files:
        filename = file.get("filename", "")
        patch = file.get("patch", "") or ""
        changes = file.get("changes", 0)

        if changes > 250:
            issues.append({
                "file_path": filename,
                "line_number": None,
                "tool": "devprobe-basic",
                "category": "maintainability",
                "severity": "medium",
                "message": "Large file change detected.",
                "recommendation": "Review this file carefully or consider splitting it into smaller changes."
            })

        if filename.endswith((".py", ".js", ".ts", ".tsx", ".jsx")):
            has_code_change = True

        if (
            "test_" in filename
            or "_test" in filename
            or ".test." in filename
            or ".spec." in filename
            or "__tests__" in filename
        ):
            has_test_change = True

        risky_keywords = [
            "password",
            "secret",
            "api_key",
            "apikey",
            "token",
            "private_key",
            "access_key"
        ]

        for keyword in risky_keywords:
            if keyword.lower() in patch.lower():
                issues.append({
                    "file_path": filename,
                    "line_number": None,
                    "tool": "devprobe-basic",
                    "category": "security",
                    "severity": "high",
                    "message": f"Possible hardcoded sensitive value related to '{keyword}'.",
                    "recommendation": "Move sensitive values to environment variables or a secrets manager."
                })

        if "console.log" in patch:
            issues.append({
                "file_path": filename,
                "line_number": None,
                "tool": "devprobe-basic",
                "category": "style",
                "severity": "low",
                "message": "console.log found in changed code.",
                "recommendation": "Remove debug logging before merging."
            })

        if "print(" in patch:
            issues.append({
                "file_path": filename,
                "line_number": None,
                "tool": "devprobe-basic",
                "category": "style",
                "severity": "low",
                "message": "print() found in changed code.",
                "recommendation": "Remove debug prints or replace with structured logging."
            })

        if "TODO" in patch or "FIXME" in patch:
            issues.append({
                "file_path": filename,
                "line_number": None,
                "tool": "devprobe-basic",
                "category": "maintainability",
                "severity": "low",
                "message": "TODO or FIXME found in changed code.",
                "recommendation": "Resolve the TODO/FIXME or create a tracking issue."
            })

    if has_code_change and not has_test_change:
        issues.append({
            "file_path": "PR-level",
            "line_number": None,
            "tool": "devprobe-basic",
            "category": "testing",
            "severity": "medium",
            "message": "Code changed without test changes.",
            "recommendation": "Add or update tests for the changed behavior."
        })

    return issues