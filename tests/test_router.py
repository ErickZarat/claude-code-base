"""Guards the router: plain messages reach the right skill, plans/proposals run on opus, nothing else picks opus alone."""

import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/eng"
ROUTER = PLUGIN / "skills/router/SKILL.md"
PLANNER = PLUGIN / "agents/planner.md"
TASK = PLUGIN / "skills/task/SKILL.md"


def frontmatter(path: Path) -> dict:
    block = path.read_text().split("---")[1]
    return dict(line.split(": ", 1) for line in block.strip().splitlines() if ": " in line)


def manual_skills() -> list[str]:
    return sorted(
        skill.parent.name for skill in PLUGIN.glob("skills/*/SKILL.md")
        if frontmatter(skill).get("disable-model-invocation") == "true"
    )


def test_router_is_model_invocable_with_a_short_description():
    meta = frontmatter(ROUTER)
    assert meta.get("disable-model-invocation") != "true"
    assert len(meta["description"]) < 200


def test_router_reaches_every_manual_eng_skill():
    text = ROUTER.read_text()
    missing = [name for name in manual_skills() if f"/eng:{name}" not in text]
    assert missing == [], f"router cannot dispatch to: {missing}"


def test_router_covers_the_companion_tools():
    text = ROUTER.read_text()
    for target in ("/opsx:propose", "/pstack:how", "/pstack:poteto-mode", "/ponytail-review", "graphify query"):
        assert target in text


def test_proposals_and_plans_run_on_opus_through_the_planner():
    router = ROUTER.read_text()
    assert re.search(r"planner.*opus", router, re.IGNORECASE)
    task_plan = TASK.read_text().split("## 3b.")[1].split("## 4.")[0]
    assert "planner" in task_plan and "opus" in task_plan


def test_router_never_picks_opus_on_its_own_for_other_work():
    text = ROUTER.read_text().lower()
    assert "ask before any other opus" in text


def test_expensive_routes_are_confirmed_first():
    text = ROUTER.read_text().lower()
    for expensive in ("/eng:review", "/eng:epic"):
        assert expensive in text
    assert "confirm" in text


def test_planner_uses_the_openspec_cli_and_the_graph():
    text = PLANNER.read_text()
    assert "openspec instructions" in text and "openspec status" in text
    assert "graphify" in text
    assert frontmatter(PLANNER)["model"] in ("sonnet", "haiku")  # opus only per call
