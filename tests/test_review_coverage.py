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
    # efficiency (must be covered even when performance-reviewer is skipped)
    "n+1 / query patterns": ["n+1"],
    "remote calls in loops": ["remote calls in loops", "calls in loops"],
    "timeouts": ["timeout"],
}

REVIEWERS_BY_DEPTH = {
    "quick": ["code-reviewer"],
    "standard": ["requirements-verifier", "code-reviewer"],  # performance-reviewer is conditional: not counted
}


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


def test_code_reviewer_checks_requirements_itself_in_quick_mode():
    text = (AGENTS / "code-reviewer.md").read_text().lower()
    assert "requirements-verifier is not running" in text
