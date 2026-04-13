"""Tests for the objective compiler harness."""

import json
import shutil

import pytest

from src.rac_compile.harness import (
    HARNESS_CASES,
    _check_js_runtime,
    format_harness_summary,
    format_harness_summary_json,
    run_compiler_harness,
)


class TestCompilerHarness:
    """Tests for harness execution and formatting."""

    def test_run_compiler_harness_all_cases_pass(self):
        """The built-in harness runs green in the current repo state."""
        summary = run_compiler_harness()
        default_cases = [case for case in HARNESS_CASES if not case.external]

        assert summary.total == len(default_cases)
        assert summary.failed == 0
        assert summary.passed == len(default_cases)
        assert "control_flow" in summary.by_category
        assert "graph" in summary.by_category
        assert "oracle" in summary.by_category
        assert "policyengine" not in summary.by_category
        assert "subgraph" in summary.by_category

    def test_run_compiler_harness_single_case(self):
        """The harness can run a selected case by name."""
        summary = run_compiler_harness(case_names=["basic_straight_line"])

        assert summary.total == 1
        assert summary.passed == 1
        assert summary.results[0].case == "basic_straight_line"

    def test_run_compiler_harness_oracle_example_case(self):
        """Example-backed oracle cases compare compiled output to references."""
        summary = run_compiler_harness(case_names=["oracle_eitc_example"])

        assert summary.total == 1
        assert summary.passed == 1
        assert summary.results[0].case == "oracle_eitc_example"

    def test_run_compiler_harness_batch_branch_case(self):
        """Harness cases can validate lowered batch execution directly."""
        summary = run_compiler_harness(case_names=["branching_batch_execution"])

        assert summary.total == 1
        assert summary.passed == 1
        assert summary.results[0].case == "branching_batch_execution"

    def test_run_compiler_harness_external_policyengine_case(self, monkeypatch):
        """External oracle cases can compare compiled output to PolicyEngine."""
        monkeypatch.setattr(
            "src.rac_compile.harness.run_policyengine_household",
            lambda inputs: {"pe_snap": 410.0},
        )

        summary = run_compiler_harness(case_names=["policyengine_snap_example"])

        assert summary.total == 1
        assert summary.passed == 1
        assert summary.results[0].case == "policyengine_snap_example"

    def test_run_compiler_harness_external_case_skips_without_dependency(
        self, monkeypatch
    ):
        """External oracle cases skip cleanly when PolicyEngine is unavailable."""

        def _raise_import_error(_inputs):
            raise ImportError("policyengine-us required for validation")

        monkeypatch.setattr(
            "src.rac_compile.harness.run_policyengine_household",
            _raise_import_error,
        )

        summary = run_compiler_harness(case_names=["policyengine_snap_example"])

        assert summary.total == 1
        assert summary.skipped == 1
        assert summary.results[0].status == "skipped"

    def test_format_harness_summary_text_and_json(self):
        """Harness summaries can be rendered for CLI output."""
        summary = run_compiler_harness(case_names=["basic_straight_line"])

        text = format_harness_summary(summary)
        payload = json.loads(format_harness_summary_json(summary))

        assert "Compiler harness score: 1/1" in text
        assert payload["score"] == "1/1"
        assert payload["results"][0]["case"] == "basic_straight_line"

    def test_check_js_runtime_detects_wrong_output(self):
        """JS harness execution catches semantic output mismatches."""
        if shutil.which("node") is None:
            pytest.skip("Node.js is required for JS runtime harness checks.")

        code = """
function calculate({ wages = 0 }) {
  return {
    tax: wages * 0.1,
    citations: [],
  };
}

export { calculate };
export default calculate;
"""

        detail = _check_js_runtime(code, {"wages": 100}, {"tax": 99})

        assert detail == "Expected JS output tax=99, got 10."

    def test_run_compiler_harness_skips_js_cases_without_node(self, monkeypatch):
        """Harness reports JS-backed cases as skipped when Node.js is unavailable."""
        monkeypatch.setattr("src.rac_compile.harness.shutil.which", lambda _: None)

        summary = run_compiler_harness(case_names=["basic_straight_line"])

        assert summary.total == 1
        assert summary.passed == 0
        assert summary.skipped == 1
        assert summary.results[0].status == "skipped"
        assert "after Python checks passed" in summary.results[0].detail
