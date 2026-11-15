"""Guards review coverage: every review depth must still check everything the original (v1.0) review checked.

Merging reviewers to save tokens must never silently drop a check. Each topic below lists phrases, any one of which
must appear in the instructions of the reviewers that run at that depth.
"""

from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/eng"
AGENTS = PLUGIN / "agents"

REQUIRED_TOPICS = {
    # requirements
    "requirements traceability": ["requirement → code → test", "requirement", "acceptance criteria"],
    "scope creep": ["scope creep"],
    "tdd evidence": ["commit history"],
    # security (parity with the secure-self-review checklist)
    "hard-coded secrets": ["hard-coded secrets"],
    "secrets or PII in logs": ["pii"],
    "backdoors": ["backdoor"],
    "disabled security controls": ["csrf"],
    "cors with credentials": ["cors"],
    "input validation": ["unvalidated input", "input validated"],
    "injection": ["injection"],
    "unsafe deserialization": ["deserializ"],
    "server-side authorization": ["authoriz"],
    "generic client errors": ["generic error"],
    "new dependencies": ["dependenc"],
    "outbound calls / telemetry": ["outbound", "telemetry"],
    "config documented": [".env.example"],
    "path traversal": ["path traversal"],
    "password hashing / crypto": ["password hashing"],
    # tests
    "untested behaviour": ["without tests"],
    "weak or weakened tests": ["weakened"],
    "flaky tests": ["non-deterministic"],
    # correctness
    "silent failures": ["silent failure"],
    "race conditions": ["race condition"],
    # architecture and design
    "interfaces / ports": ["interface"],
    "duplication / reuse": ["duplicated logic"],
    "type design": ["type design", "encapsulation"],
    "needless complexity": ["needless complexity", "simplif"],
    # readability
    "naming": ["names"],
    "comments explain why": ["why"],
    "stale comments": ["stale", "inaccurate comment"],
    "leftover debug code": ["debug code"],
    # spec-driven extras (v2.8)
    "non-functional requirements": ["non-functional requirements"],
    "api contract compatibility": ["backwards compatib"],
    "scenario traceability": ["trace.py"],
    # efficiency (must be covered even when risk-reviewer is not running — quick depth)
    "n+1 / query patterns": ["n+1"],
    "remote calls in loops": ["remote calls in loops", "calls in loops"],
    "timeouts": ["timeout"],
}

REVIEWERS_BY_DEPTH = {
    "quick": ["correctness-reviewer"],  # only when explicitly requested
    "standard": ["correctness-reviewer", "risk-reviewer"],  # v4.0: two reviewers instead of four
    # v4.0 comparison release: the previous four stay available with --reviewers four.
    "four": ["requirements-verifier", "performance-reviewer", "security-reviewer", "code-reviewer"],
}
ALL_DEDICATED_REVIEWERS = REVIEWERS_BY_DEPTH["standard"]
REVIEW_ONCE = PLUGIN / "skills/review-once/SKILL.md"
SECURITY_TOPICS = ["hard-coded secrets", "pii", "backdoor", "csrf", "cors", "injection", "deserializ", "authoriz",
                   "generic error", "dependenc", "outbound", ".env.example", "path traversal", "password hashing"]


def instructions_for(agent_names):
    return " ".join((AGENTS / f"{name}.md").read_text() for name in agent_names).lower()


@pytest.mark.parametrize("depth", list(REVIEWERS_BY_DEPTH))
def test_every_depth_covers_every_required_topic(depth):
    text = instructions_for(REVIEWERS_BY_DEPTH[depth])
    missing = [topic for topic, phrases in REQUIRED_TOPICS.items() if not any(phrase in text for phrase in phrases)]
    assert missing == [], f"{depth} review no longer checks: {missing}"


@pytest.mark.parametrize("agent_file", sorted(AGENTS.glob("*.md")), ids=lambda path: path.stem)
def test_reviewers_never_cap_the_number_of_findings(agent_file):
    text = agent_file.read_text().lower()
    assert "max 10 findings" not in text and "max 15 findings" not in text
    assert "every finding" in text or "fix-verifier" in agent_file.stem


def test_correctness_reviewer_covers_risk_basics_itself_in_quick_mode():
    text = (AGENTS / "correctness-reviewer.md").read_text().lower()
    assert "risk-reviewer is not running" in text


def test_merged_reviewers_must_show_they_covered_every_section():
    correctness = (AGENTS / "correctness-reviewer.md").read_text()
    risk = (AGENTS / "risk-reviewer.md").read_text()
    # Requirements work is tedious and gets skipped first when merged: its table is mandatory output.
    assert "| ID | Requirement | Status | Code | Test | Note |" in correctness
    assert "Checked:" in correctness and "Checked:" in risk
    # Security comes first in the shared risk pass.
    assert risk.index("## Security") < risk.index("## Performance")


def test_comparison_option_keeps_the_previous_four_reviewers():
    text = REVIEW_ONCE.read_text()
    assert "--reviewers four" in text
    for reviewer in REVIEWERS_BY_DEPTH["four"]:
        assert reviewer in text


def depth_row(depth):
    return next(line for line in REVIEW_ONCE.read_text().splitlines() if line.startswith(f"| **{depth}**"))


@pytest.mark.parametrize("depth", ["standard", "thorough"])
def test_standard_and_thorough_run_every_dedicated_reviewer(depth):
    row = depth_row(depth)
    for reviewer in ALL_DEDICATED_REVIEWERS:
        assert reviewer in row, f"{depth} no longer runs {reviewer}"
    assert "only if" not in row.split("|")[2] and "if triage" not in row


def test_pr_review_toolkit_runs_only_in_thorough_reviews():
    # v3.3: the toolkit duplicated the dedicated reviewers' findings at standard depth.
    assert "pr-review-toolkit" not in depth_row("standard").split("|")[2]
    assert "pr-review-toolkit" in depth_row("thorough")


def test_pre_reviewer_uses_the_shared_checklist_with_fresh_context():
    text = (AGENTS / "pre-reviewer.md").read_text()
    assert "model: sonnet" in text
    assert "checklists/self-check.md" in text
    assert "every finding" in text.lower()


def test_pre_review_runs_once_per_pr_not_per_task():
    dod = (PLUGIN / "skills/dod/SKILL.md").read_text().lower()
    task = (PLUGIN / "skills/task/SKILL.md").read_text().lower()
    assert "pre-reviewer" in dod and "once per pr" in dod
    assert "pre-reviewer" not in task.split("## 4.")[1].split("## 5.")[0]


@pytest.mark.parametrize("agent", ["risk-reviewer", "security-reviewer"])
def test_security_reviewing_agent_covers_the_full_checklist(agent):
    text = (AGENTS / f"{agent}.md").read_text().lower()
    missing = [topic for topic in SECURITY_TOPICS if topic not in text]
    assert missing == []


def test_quick_is_never_chosen_automatically():
    text = REVIEW_ONCE.read_text()
    assert "only when the user explicitly asks" in text.lower()


SQL_INJECTION_TOPICS = ["dynamic sql candidates", "bound parameters", "string templates", "order by", "allowlist",
                        "native queries", "like", "stored procedures"]


@pytest.mark.parametrize("agent", ["risk-reviewer", "correctness-reviewer", "security-reviewer", "code-reviewer"])
def test_sql_injection_is_checked_concretely(agent):
    text = (AGENTS / f"{agent}.md").read_text().lower()
    missing = [topic for topic in SQL_INJECTION_TOPICS if topic not in text]
    assert missing == [], f"{agent} SQL injection check is missing: {missing}"


# --- v2.10: the writer's self-check covers everything the reviewers check ---------------------------

SELF_CHECK = PLUGIN / "checklists/self-check.md"


def test_self_check_covers_every_review_topic():
    text = SELF_CHECK.read_text().lower()
    missing = [topic for topic, phrases in REQUIRED_TOPICS.items() if not any(phrase in text for phrase in phrases)]
    assert missing == [], f"developers are not told to check: {missing}"


def test_self_check_covers_the_sql_injection_details():
    text = SELF_CHECK.read_text().lower()
    missing = [topic for topic in SQL_INJECTION_TOPICS if topic not in text]
    assert missing == [], missing
