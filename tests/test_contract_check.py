"""Behaviour tests for the API contract breaking-change check shipped to projects (eng_contract_check.py)."""

import importlib.util
import sys
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "plugins/eng/template/.github"
spec = importlib.util.spec_from_file_location("eng_contract_check", TEMPLATE / "scripts/eng_contract_check.py")
contract_check = importlib.util.module_from_spec(spec)
sys.modules["eng_contract_check"] = contract_check
spec.loader.exec_module(contract_check)

OPENAPI = "openapi: 3.0.3\ninfo: {title: shop, version: 1.0.0}\n"


def classify(paths, contents=None):
    contents = contents or {}
    return contract_check.classify_contract_files(paths, lambda path: contents.get(path, ""))


def test_classifies_proto_openapi_graphql_and_avro_files():
    found = classify(["api/refund.proto", "docs/openapi.yaml", "src/Main.kt", "schema/shop.graphql",
                      "events/refund.avsc", "config/app.yaml", "spec/public-api.yml"],
                     {"spec/public-api.yml": OPENAPI, "config/app.yaml": "server: {port: 8080}\n"})
    assert found == {"proto": ["api/refund.proto"], "openapi": ["docs/openapi.yaml", "spec/public-api.yml"],
                     "graphql": ["schema/shop.graphql"], "avro": ["events/refund.avsc"]}


def test_plans_buf_breaking_when_buf_config_exists():
    checks, notes = contract_check.plan_checks({"proto": ["api/refund.proto"]}, "main",
                                              has_buf_config=True, existed_at_base=lambda path: True)
    command = checks[0].command
    assert command[:3] == ["docker", "run", "--rm"] and "bufbuild/buf" in command
    assert "breaking" in command and ".git#ref=origin/main" in " ".join(command)


def test_warns_when_proto_changes_without_buf_config():
    checks, notes = contract_check.plan_checks({"proto": ["api/refund.proto"]}, "main",
                                              has_buf_config=False, existed_at_base=lambda path: True)
    assert checks == [] and any("buf.yaml" in note for note in notes)


def test_plans_oasdiff_for_each_changed_openapi_file_that_existed_before():
    checks, notes = contract_check.plan_checks({"openapi": ["docs/openapi.yaml", "docs/new-api.yaml"]}, "main",
                                              has_buf_config=False,
                                              existed_at_base=lambda path: path == "docs/openapi.yaml")
    assert len(checks) == 1
    assert "tufin/oasdiff" in checks[0].command and "breaking" in checks[0].command
    assert checks[0].base_file == "docs/openapi.yaml"
    assert any("new-api.yaml" in note and "new" in note for note in notes)


def test_graphql_and_avro_are_reported_for_manual_review():
    checks, notes = contract_check.plan_checks({"graphql": ["schema.graphql"], "avro": ["e.avsc"]}, "main",
                                              has_buf_config=False, existed_at_base=lambda path: True)
    assert checks == [] and any("schema.graphql" in note for note in notes) and any("e.avsc" in note for note in notes)


@pytest.mark.parametrize("approved, expected_exit", [(False, 1), (True, 0)])
def test_breaking_change_fails_unless_explicitly_approved(approved, expected_exit):
    body = "Breaking-change: approved — v2 endpoint, clients migrated" if approved else "Closes #4"
    assert contract_check.exit_code(breaking_found=True, pr_body=body) == expected_exit


def test_no_breaking_change_passes():
    assert contract_check.exit_code(breaking_found=False, pr_body="") == 0


def test_workflow_passes_pr_data_via_env_and_fetches_history():
    workflow = (TEMPLATE / "workflows/eng-contracts.yml").read_text()
    assert "fetch-depth: 0" in workflow
    assert "PR_BODY: ${{ github.event.pull_request.body }}" in workflow
    assert "BASE_REF: ${{ github.base_ref }}" in workflow
    assert "${{" not in workflow.split("run:", 1)[1]
