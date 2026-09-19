"""One workflow for manual scans and, later, queued scans. No HTTP dependencies."""

import logging
from collections import Counter
from datetime import UTC, datetime
from time import perf_counter

from app.core.errors import ScanExecutionError, ServiceError
from app.db.memory_store import MemoryScanStore
from app.schemas.pull_request import ChangedFileResponse
from app.schemas.scan import ScanResponse, TriggerSource
from app.services import analyzer_service, github_service, scoring_service

logger = logging.getLogger(__name__)
store = MemoryScanStore()
MAX_PATCH_CHARACTERS = 16_000_000


def create_pending_scan(
    repo_url: str, pr_number: int, trigger_source: TriggerSource = "manual"
) -> ScanResponse:
    owner, repo = github_service.parse_github_url(repo_url)
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        raise ServiceError("Pull request number must be a positive integer.", 422)
    return store.create(
        ScanResponse(
            repo_url=f"https://github.com/{owner}/{repo}",
            pr_number=pr_number,
            trigger_source=trigger_source,
            created_at=datetime.now(UTC),
        )
    )


def create_scan(repo_url: str, pr_number: int) -> ScanResponse:
    scan = create_pending_scan(repo_url, pr_number)
    return execute_scan(scan.id)


def get_scan(scan_id: int) -> ScanResponse:
    scan = store.get(scan_id)
    if scan is None:
        raise ServiceError("Scan not found.", 404)
    return scan


def execute_scan(scan_id: int) -> ScanResponse:
    scan, claimed = store.claim(scan_id)
    if not claimed:
        return scan  # Repeated task delivery must not run the same scan twice.
    started = perf_counter()
    logger.info("scan_started scan_id=%s pr_number=%s", scan.id, scan.pr_number)
    try:
        pull = github_service.fetch_pull_request(scan.repo_url, scan.pr_number)
        if pull["changed_files"] > 3000:
            raise ServiceError("This PR exceeds GitHub's 3000-file retrieval limit.", 422)
        files = [
            ChangedFileResponse.model_validate(file)
            for file in github_service.fetch_pr_files(scan.repo_url, scan.pr_number)
        ]
        if len(files) != pull["changed_files"] or len({f.filename for f in files}) != len(files):
            raise ServiceError(
                "GitHub returned an incomplete file list. Please retry the scan.", 409
            )
        latest = github_service.fetch_pull_request(scan.repo_url, scan.pr_number)
        if any(latest[key] != pull[key] for key in ("head_sha", "base_sha", "changed_files")):
            raise ServiceError("The PR changed during retrieval. Please retry the scan.", 409)
        if sum(len(f.patch or "") for f in files) > MAX_PATCH_CHARACTERS:
            raise ServiceError("PR patches exceed the MVP analysis size limit.", 422)

        scan.head_sha, scan.base_sha = pull["head_sha"], pull["base_sha"]
        scan.changed_files_count = len(files)
        scan.additions = sum(f.additions for f in files)
        scan.deletions = sum(f.deletions for f in files)
        scan.total_changed_lines = scan.additions + scan.deletions
        scan.files_with_patch = sum(bool(f.patch) for f in files)
        scan.files_without_patch = len(files) - scan.files_with_patch
        scan.analysis_warnings = [
            "Basic findings are heuristics, not confirmed vulnerabilities or proof of coverage.",
            "Only added lines in GitHub-provided patches are inspected; patches may be incomplete.",
        ]
        if scan.files_without_patch:
            scan.analysis_warnings.append(
                f"{scan.files_without_patch} file(s) have no textual patch; line checks skipped."
            )
        scan.issues = analyzer_service.analyze_changed_files(files)
        scan.total_issues = len(scan.issues)
        counts = Counter(issue.category for issue in scan.issues)
        for category in (
            "security",
            "complexity",
            "style",
            "testing",
            "maintainability",
            "documentation",
        ):
            setattr(scan, f"{category}_count", counts[category])
        scan.risk_score, scan.risk_level = scoring_service.calculate_risk(
            scan.issues,
            scan.changed_files_count,
            scan.total_changed_lines,
        )
        scan.status = "completed"
    except Exception as error:
        safe_error = (
            error
            if isinstance(error, ServiceError)
            else ServiceError(
                "Scan failed due to an internal error.",
                500,
            )
        )
        scan.status = "failed"
        scan.failure_reason = safe_error.message
        # Do not expose a partly scored result as a completed result.
        scan.issues = []
        scan.total_issues = 0
        scan.risk_score = None
        scan.risk_level = None
        for category in (
            "security",
            "complexity",
            "style",
            "testing",
            "maintainability",
            "documentation",
        ):
            setattr(scan, f"{category}_count", 0)
        logger.error("scan_failed scan_id=%s error_type=%s", scan.id, type(error).__name__)
        raise ScanExecutionError(scan.id, safe_error) from None
    finally:
        scan.completed_at = datetime.now(UTC)
        scan.scan_duration_seconds = round(perf_counter() - started, 6)
        store.save(scan)
        logger.info(
            "scan_finished scan_id=%s status=%s duration=%s",
            scan.id,
            scan.status,
            scan.scan_duration_seconds,
        )
    return scan
