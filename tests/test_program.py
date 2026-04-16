"""Tests for multi-file RAC program loading and compilation."""

import json
from pathlib import Path

import pytest

from src.rac_compile.compile_model import CompilationError
from src.rac_compile.program import load_rac_program
from src.rac_compile.rule_bindings import RuleBindingError


class TestRacProgram:
    """Tests for file-graph loading and compilation."""

    def test_working_families_example_graph_compiles_and_runs(self):
        """The shipped multi-file example compiles with qualified bindings."""
        entry = (
            Path(__file__).parent.parent
            / "examples"
            / "working_families"
            / "benefit_amount.rac"
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator(
            parameter_overrides={"phase_in_rate.rate": 0.25},
            outputs=["benefit_amount"],
        ).generate()

        exec(code, namespace)

        result = namespace["calculate"](
            earned_income=4000,
            has_qualifying_child=True,
        )
        assert result["benefit_amount"] == 1000

        result = namespace["calculate"](
            earned_income=4000,
            has_qualifying_child=False,
        )
        assert result["benefit_amount"] == 0

    def test_working_families_example_lowering_preserves_module_identities(self):
        """The shipped multi-file example lowers with real file identities intact."""
        entry = (
            Path(__file__).parent.parent
            / "examples"
            / "working_families"
            / "benefit_amount.rac"
        )

        lowered = load_rac_program(entry).to_lowered_program(
            parameter_overrides={"phase_in_rate.rate": 0.25},
            outputs=["benefit_amount"],
        )

        assert [output.name for output in lowered.outputs] == ["benefit_amount"]
        assert {parameter.module_identity for parameter in lowered.parameters} == {
            "phase_in_cap",
            "phase_in_rate",
        }

    def test_load_rac_program_defaults_to_computed_outputs_only(self, tmp_path):
        """Default public outputs should not include free inputs from source files."""
        entry = tmp_path / "snap_child_support_deduction.rac"
        entry.write_text(
            """
snap_child_support_payments_made:
  entity: SnapUnit
  period: Month
  dtype: Money

snap_state_uses_child_support_deduction:
  entity: SnapUnit
  period: Month
  dtype: Boolean

snap_child_support_deduction:
  entity: SnapUnit
  period: Month
  dtype: Money
  from 2022-01-01:
    if snap_state_uses_child_support_deduction: snap_child_support_payments_made else: 0
"""
        )

        program = load_rac_program(entry)
        lowered = program.to_lowered_program()

        assert program.default_outputs == ["snap_child_support_deduction"]
        assert [output.name for output in lowered.outputs] == [
            "snap_child_support_deduction"
        ]
        assert {compiled_input.name for compiled_input in lowered.inputs} == {
            "snap_child_support_payments_made",
            "snap_state_uses_child_support_deduction",
        }

    def test_load_rac_program_supports_inline_rac_conditional_expressions(
        self, tmp_path
    ):
        """Inline `if cond: a else: b` RAC expressions compile without rewrites."""
        entry = tmp_path / "snap_child_support_deduction.rac"
        entry.write_text(
            """
snap_child_support_payments_made:
  entity: SnapUnit
  period: Month
  dtype: Money

snap_state_uses_child_support_deduction:
  entity: SnapUnit
  period: Month
  dtype: Boolean

snap_child_support_deduction:
  entity: SnapUnit
  period: Month
  dtype: Money
  from 2022-01-01:
    if snap_state_uses_child_support_deduction: snap_child_support_payments_made else: 0
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](
            snap_child_support_payments_made=500,
            snap_state_uses_child_support_deduction=True,
        )["snap_child_support_deduction"] == 500
        assert namespace["calculate"](
            snap_child_support_payments_made=500,
            snap_state_uses_child_support_deduction=False,
        )["snap_child_support_deduction"] == 0

    def test_load_rac_program_supports_chained_inline_rac_conditionals(
        self, tmp_path
    ):
        """Chained inline RAC conditionals collapse into one compiled expression."""
        entry = tmp_path / "need_standard.rac"
        entry.write_text(
            """
number_of_children_in_assistance_unit:
  entity: TanfUnit
  period: Month
  dtype: Integer

need_standard:
  entity: TanfUnit
  period: Month
  dtype: Money
  from 2026-04-02:
    if number_of_children_in_assistance_unit == 0: 0 else:
    if number_of_children_in_assistance_unit == 1: 117 else:
    if number_of_children_in_assistance_unit == 2: 245 else:
    999
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](number_of_children_in_assistance_unit=0)[
            "need_standard"
        ] == 0
        assert namespace["calculate"](number_of_children_in_assistance_unit=2)[
            "need_standard"
        ] == 245
        assert namespace["calculate"](number_of_children_in_assistance_unit=3)[
            "need_standard"
        ] == 999

    def test_load_rac_program_supports_multiline_expression_continuations(
        self, tmp_path
    ):
        """Bare expression lines can continue across multiple lines at one indent."""
        entry = tmp_path / "flag.rac"
        entry.write_text(
            """
a:
  entity: Person
  period: Month
  dtype: Boolean

b:
  entity: Person
  period: Month
  dtype: Boolean

flag:
  entity: Person
  period: Month
  dtype: Boolean
  from 2026-01-01:
    a and
    b
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](a=True, b=True)["flag"] is True
        assert namespace["calculate"](a=True, b=False)["flag"] is False

    def test_load_rac_program_supports_inline_if_elif_else_statements(
        self, tmp_path
    ):
        """Single-line `if` / `elif` / `else` branches normalize into real blocks."""
        entry = tmp_path / "phaseout_percentage.rac"
        entry.write_text(
            """
qualifying_child_count:
  entity: TaxUnit
  period: Year
  dtype: Integer

phaseout_pct_no_children:
  from 2009-01-01: 0.0765

phaseout_pct_1_child:
  from 2009-01-01: 0.1598

phaseout_pct_2_children:
  from 2009-01-01: 0.2106

phaseout_pct_3_plus_children:
  from 2009-01-01: 0.2106

phaseout_percentage:
  entity: TaxUnit
  period: Year
  dtype: Rate
  from 2009-01-01:
    if qualifying_child_count >= 3: phaseout_pct_3_plus_children
    elif qualifying_child_count == 2: phaseout_pct_2_children
    elif qualifying_child_count == 1: phaseout_pct_1_child
    else: phaseout_pct_no_children
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](qualifying_child_count=0)[
            "phaseout_percentage"
        ] == 0.0765
        assert namespace["calculate"](qualifying_child_count=2)[
            "phaseout_percentage"
        ] == 0.2106
        assert namespace["calculate"](qualifying_child_count=4)[
            "phaseout_percentage"
        ] == 0.2106

    def test_load_rac_program_compiles_cross_file_dependencies(self, tmp_path):
        """Entry files can compile imported helper variables and parameters."""
        shared = tmp_path / "shared.rac"
        shared.write_text(
            """
rate:
  source: "shared-rate"
  from 2024-01-01: 0.1

taxable_income:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages - deduction
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
import "./shared.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return taxable_income * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        result = namespace["calculate"](wages=1000, deduction=100)
        assert result["tax"] == 90
        assert "taxable_income" not in result

    def test_load_rac_program_resolves_spec_style_variable_imports(self, tmp_path):
        """Per-variable `imports:` blocks resolve through statute-root paths."""
        statute_root = tmp_path / "statute" / "26" / "62"
        statute_root.mkdir(parents=True)
        (statute_root / "62.rac").write_text(
            """
adjusted_gross_income:
  entity: TaxUnit
  period: Year
  dtype: Money
"""
        )
        target_root = tmp_path / "statute" / "26" / "21" / "a" / "2"
        target_root.mkdir(parents=True)
        entry = target_root / "A.rac"
        entry.write_text(
            """
first_reduction:
  imports:
    - 26/62#adjusted_gross_income
  entity: TaxUnit
  period: Year
  dtype: Rate
  from 2002-01-01:
    adjusted_gross_income >= 15000
"""
        )

        lowered = load_rac_program(entry).to_lowered_program(
            outputs=["first_reduction"]
        )

        assert [compiled_input.name for compiled_input in lowered.inputs] == [
            "statute_26_62_62_adjusted_gross_income"
        ]
        assert lowered.outputs[0].module_identity == "statute/26/21/a/2/A"

    def test_load_rac_program_resolves_root_qualified_top_level_imports(
        self, tmp_path
    ):
        """Top-level `imports:` blocks can target root-qualified citation paths."""
        dependency_root = tmp_path / "statute" / "crs" / "26-2-703"
        dependency_root.mkdir(parents=True)
        (dependency_root / "12.rac").write_text(
            """
contract_is_entered_into_by_participant_and_county_department:
  entity: Person
  period: Month
  dtype: Boolean

contract_is_pursuant_to_section_26_2_708:
  entity: Person
  period: Month
  dtype: Boolean

is_individual_responsibility_contract:
  entity: Person
  period: Month
  dtype: Boolean
  from 2026-04-03:
    contract_is_entered_into_by_participant_and_county_department and
    contract_is_pursuant_to_section_26_2_708
"""
        )
        entry_root = tmp_path / "statute" / "crs" / "26-2-711" / "1" / "a"
        entry_root.mkdir(parents=True)
        entry = entry_root / "I.rac"
        entry.write_text(
            """
imports:
  - statute/crs/26-2-703/12#is_individual_responsibility_contract

participant_fails_to_comply_with_terms_and_conditions_of_contract:
  entity: Person
  period: Month
  dtype: Boolean

good_cause_exists_as_determined_by_county:
  entity: Person
  period: Month
  dtype: Boolean

participant_is_subject_to_sanction_for_noncompliance_with_individual_responsibility_contract:
  entity: Person
  period: Month
  dtype: Boolean
  from 2026-04-03:
    participant_fails_to_comply_with_terms_and_conditions_of_contract and
    is_individual_responsibility_contract and
    not good_cause_exists_as_determined_by_county
"""
        )

        lowered = load_rac_program(entry).to_lowered_program(
            outputs=[
                "participant_is_subject_to_sanction_for_noncompliance_with_individual_responsibility_contract"
            ]
        )

        assert {
            compiled_input.public_name or compiled_input.name
            for compiled_input in lowered.inputs
        } == {
            "participant_fails_to_comply_with_terms_and_conditions_of_contract",
            "good_cause_exists_as_determined_by_county",
            (
                "statute/crs/26-2-703/12."
                "contract_is_entered_into_by_participant_and_county_department"
            ),
            "statute/crs/26-2-703/12.contract_is_pursuant_to_section_26_2_708",
        }
        assert (
            "statute/crs/26-2-703/12.is_individual_responsibility_contract"
            not in {
                compiled_input.public_name or compiled_input.name
                for compiled_input in lowered.inputs
            }
        )
        assert lowered.outputs[0].module_identity == "statute/crs/26-2-711/1/a/I"

        namespace: dict[str, object] = {}
        code = load_rac_program(entry).to_python_generator(
            outputs=[
                "participant_is_subject_to_sanction_for_noncompliance_with_individual_responsibility_contract"
            ]
        ).generate()

        exec(code, namespace)

        result = namespace["calculate"](
            **{
                (
                    "statute/crs/26-2-703/12."
                    "contract_is_entered_into_by_participant_and_county_department"
                ): True,
                (
                    "statute/crs/26-2-703/12."
                    "contract_is_pursuant_to_section_26_2_708"
                ): True,
                (
                    "participant_fails_to_comply_with_terms_and_conditions_of_"
                    "contract"
                ): True,
                "good_cause_exists_as_determined_by_county": False,
            }
        )

        assert result[
            "participant_is_subject_to_sanction_for_noncompliance_with_individual_responsibility_contract"
        ] is True

    def test_selected_outputs_prune_unreachable_imported_variables(self, tmp_path):
        """Graph pruning excludes unreachable imported variables before validation."""
        shared = tmp_path / "shared.rac"
        shared.write_text(
            """
rate:
  source: "shared-rate"
  from 2024-01-01: 0.1

taxable_income:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages - deduction

bonus:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    while wages > 0:
      return wages
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
import "./shared.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return taxable_income * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator(outputs=["tax"]).generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=1000, deduction=100)["tax"] == 90

    def test_load_rac_program_rejects_missing_import(self, tmp_path):
        """Missing imported files fail with a user-facing error."""
        entry = tmp_path / "main.rac"
        entry.write_text('import "./missing.rac"\n')

        with pytest.raises(CompilationError, match="was not found"):
            load_rac_program(entry)

    def test_load_rac_program_rejects_non_rac_entry_file(self, tmp_path):
        """Entrypoints must use the .rac extension."""
        entry = tmp_path / "main.txt"
        entry.write_text("tax:\n  entity: Person\n  period: Year\n  dtype: Money\n")

        with pytest.raises(CompilationError, match="must use the \\.rac extension"):
            load_rac_program(entry)

    def test_load_rac_program_rejects_non_rac_imports(self, tmp_path):
        """Imported files must also use the .rac extension."""
        (tmp_path / "shared.txt").write_text(
            """
rate:
  source: "shared-rate"
  from 2024-01-01: 0.1
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text('import "./shared.txt"\n')

        with pytest.raises(CompilationError, match="must use the \\.rac extension"):
            load_rac_program(entry)

    def test_load_rac_program_rejects_import_cycles(self, tmp_path):
        """Import cycles fail loudly instead of recursing forever."""
        (tmp_path / "a.rac").write_text('import "./b.rac"\n')
        (tmp_path / "b.rac").write_text('import "./a.rac"\n')

        with pytest.raises(CompilationError, match="Import cycle detected"):
            load_rac_program(tmp_path / "a.rac")

    def test_load_rac_program_rejects_duplicate_symbols(self, tmp_path):
        """Plain imports still reject ambiguous duplicate symbol exposure."""
        (tmp_path / "left.rac").write_text(
            """
shared:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return 1
"""
        )
        (tmp_path / "right.rac").write_text(
            """
shared:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return 2
"""
        )
        (tmp_path / "main.rac").write_text(
            """
import "./left.rac"
import "./right.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return shared
"""
        )

        with pytest.raises(CompilationError, match="Plain import scope collision"):
            load_rac_program(tmp_path / "main.rac").to_compile_model()

    def test_load_rac_program_supports_aliased_duplicate_symbols(self, tmp_path):
        """Aliased imports can expose duplicate names without global collisions."""
        (tmp_path / "left.rac").write_text(
            """
rate:
  source: "left-rate"
  from 2024-01-01: 0.1
"""
        )
        (tmp_path / "right.rac").write_text(
            """
rate:
  source: "right-rate"
  from 2024-01-01: 0.2
"""
        )
        (tmp_path / "main.rac").write_text(
            """
import "./left.rac" as left
import "./right.rac" as right

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * left.rate + wages * right.rate
"""
        )

        namespace = {}
        code = load_rac_program(tmp_path / "main.rac").to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=100)["tax"] == 30

    def test_load_rac_program_rejects_duplicate_leaf_module_identities(
        self, tmp_path
    ):
        """Programs fail loudly when two files share the same subsection leaf."""
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "shared.rac").write_text(
            """
rate:
  source: "left-rate"
  from 2024-01-01: 0.1
"""
        )
        (right / "shared.rac").write_text(
            """
bonus:
  source: "right-bonus"
  from 2024-01-01: 2
"""
        )
        entry = tmp_path / "benefit_amount.rac"
        entry.write_text(
            """
import "./left/shared.rac"
import "./right/shared.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages
"""
        )

        with pytest.raises(CompilationError) as exc_info:
            load_rac_program(entry).to_compile_model()
        message = str(exc_info.value)
        assert "Module identity collision" in message
        assert "'shared'" in message
        assert str(left / "shared.rac") in message
        assert str(right / "shared.rac") in message
        assert "rename" in message.lower()

    def test_load_rac_program_rejects_normalized_module_identity_collision(
        self, tmp_path
    ):
        """Fail loudly when two distinct identities normalize to the same prefix."""
        statute_dir = tmp_path / "statute" / "us"
        statute_dir.mkdir(parents=True)
        (statute_dir / "bar-baz.rac").write_text(
            """
rate_a:
  source: "rate-a"
  from 2024-01-01: 0.1
"""
        )
        (statute_dir / "bar_baz.rac").write_text(
            """
rate_b:
  source: "rate-b"
  from 2024-01-01: 0.2
"""
        )
        entry = tmp_path / "statute" / "us" / "entry.rac"
        entry.write_text(
            """
import "./bar-baz.rac"
import "./bar_baz.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages
"""
        )

        with pytest.raises(CompilationError) as exc_info:
            load_rac_program(entry).to_compile_model()
        message = str(exc_info.value)
        assert "Module identity collision after normalization" in message
        # Both distinct identities should be called out.
        assert "bar-baz" in message
        assert "bar_baz" in message
        # Both file paths should be included as well.
        assert str(statute_dir / "bar-baz.rac") in message
        assert str(statute_dir / "bar_baz.rac") in message
        # The internal symbol prefix that collided should be shown.
        assert "statute_us_bar_baz" in message
        # The remediation suggestion should be present.
        assert "rename" in message.lower()

    def test_load_rac_program_lowered_bundle_preserves_module_identity(self, tmp_path):
        """Lowered program metadata keeps leaf-derived rule identity per node."""
        (tmp_path / "shared.rac").write_text(
            """
source:
  citation: "26 USC shared"

rate:
  source: "shared-rate"
  from 2024-01-01: 0.1

taxable_income:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages - deduction
"""
        )
        entry = tmp_path / "benefit_amount.rac"
        entry.write_text(
            """
import "./shared.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return taxable_income * rate
"""
        )

        payload = json.loads(load_rac_program(entry).to_lowered_program().to_json())

        assert [parameter["name"] for parameter in payload["parameters"]] == [
            "shared_rate"
        ]
        assert payload["parameters"][0]["module_identity"] == "shared"
        assert {
            computation["name"]: computation["module_identity"]
            for computation in payload["computations"]
        } == {
            "shared_taxable_income": "shared",
            "tax": "benefit_amount",
        }
        assert payload["outputs"] == [
            {
                "name": "tax",
                "variable_name": "tax",
                "value_kind": "number",
                "module_identity": "benefit_amount",
            }
        ]

    def test_load_rac_program_respects_explicit_exports_and_selective_imports(
        self, tmp_path
    ):
        """Selective imports can only bind symbols that a module exports."""
        (tmp_path / "shared.rac").write_text(
            """
export rate_public, taxable_income

rate_public:
  source: "shared-rate"
  from 2024-01-01: 0.1

hidden_rate:
  source: "hidden-rate"
  from 2024-01-01: 0.2

taxable_income:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages - deduction
"""
        )
        (tmp_path / "main.rac").write_text(
            """
from "./shared.rac" import rate_public as rate, taxable_income

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return taxable_income * rate
"""
        )

        namespace = {}
        code = load_rac_program(tmp_path / "main.rac").to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=1000, deduction=100)["tax"] == 90

    def test_load_rac_program_resolves_qualified_parameter_bindings(self, tmp_path):
        """Imported source-only parameters bind through module_identity.symbol."""
        (tmp_path / "shared.rac").write_text(
            """
rate:
  source: "external/rate"
"""
        )
        entry = tmp_path / "benefit_amount.rac"
        entry.write_text(
            """
import "./shared.rac"

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator(
            parameter_overrides={"shared.rate": 0.25}
        ).generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=100)["tax"] == 25

    def test_load_rac_program_rejects_ambiguous_bare_parameter_bindings(
        self, tmp_path
    ):
        """Bare source-only names fail when more than one module defines them."""
        (tmp_path / "left.rac").write_text(
            """
rate:
  source: "left-rate"
"""
        )
        (tmp_path / "right.rac").write_text(
            """
rate:
  source: "right-rate"
"""
        )
        entry = tmp_path / "benefit_amount.rac"
        entry.write_text(
            """
import "./left.rac" as left
import "./right.rac" as right

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages
"""
        )

        with pytest.raises(
            RuleBindingError,
            match="Rule binding target 'rate' is ambiguous",
        ):
            load_rac_program(entry).to_compile_model(parameter_overrides={"rate": 0.25})

    def test_load_rac_program_rejects_selective_import_of_hidden_symbol(self, tmp_path):
        """Selective imports fail loudly when the target file does not export a name."""
        (tmp_path / "shared.rac").write_text(
            """
export rate_public

rate_public:
  source: "shared-rate"
  from 2024-01-01: 0.1

hidden_rate:
  source: "hidden-rate"
  from 2024-01-01: 0.2
"""
        )
        (tmp_path / "main.rac").write_text(
            """
from "./shared.rac" import hidden_rate

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * hidden_rate
"""
        )

        with pytest.raises(CompilationError, match="non-exported symbol 'hidden_rate'"):
            load_rac_program(tmp_path / "main.rac").to_compile_model()

    def test_load_rac_program_supports_export_aliases_for_imports_and_outputs(
        self, tmp_path
    ):
        """Export aliases define both import names and public result keys."""
        (tmp_path / "shared.rac").write_text(
            """
export private_rate as rate

private_rate:
  source: "shared-rate"
  from 2024-01-01: 0.1
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
from "./shared.rac" import rate
export tax as benefit_amount

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        result = namespace["calculate"](wages=100)
        assert result["benefit_amount"] == 10
        assert "tax" not in result

    def test_load_rac_program_select_output_uses_public_export_aliases(self, tmp_path):
        """Selected outputs follow the public export surface, not internal names."""
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
export tax as benefit_amount

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * 0.1

bonus:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * 0.5
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator(
            outputs=["benefit_amount"]
        ).generate()

        exec(code, namespace)

        result = namespace["calculate"](wages=100)
        assert result == {"benefit_amount": 10, "citations": []}

        with pytest.raises(
            CompilationError,
            match="Unknown exported output variable\\(s\\): tax",
        ):
            load_rac_program(entry).to_compile_model(outputs=["tax"])

    def test_load_rac_program_supports_module_re_exports(self, tmp_path):
        """Intermediate modules can re-export imported symbols without wrappers."""
        (tmp_path / "base.rac").write_text(
            """
export private_rate as rate

private_rate:
  source: "base-rate"
  from 2024-01-01: 0.1
"""
        )
        (tmp_path / "surface.rac").write_text(
            """
export from "./base.rac" import rate
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
from "./surface.rac" import rate

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=100)["tax"] == 10

    def test_load_rac_program_supports_entry_re_exported_public_outputs(self, tmp_path):
        """Entry modules can publish imported outputs through re-exports."""
        (tmp_path / "upstream.rac").write_text(
            """
export tax as upstream_benefit

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * 0.1
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
export from "./upstream.rac" import upstream_benefit as benefit_amount
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=100) == {
            "benefit_amount": 10,
            "citations": [],
        }

    def test_load_rac_program_re_exported_outputs_keep_upstream_module_identity(
        self, tmp_path
    ):
        """Public outputs exposed through re-exports preserve their source rule."""
        (tmp_path / "upstream.rac").write_text(
            """
export tax as upstream_benefit

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * 0.1
"""
        )
        entry = tmp_path / "benefit_amount.rac"
        entry.write_text(
            """
export from "./upstream.rac" import upstream_benefit as benefit_amount
"""
        )

        payload = json.loads(load_rac_program(entry).to_lowered_program().to_json())

        assert payload["outputs"] == [
            {
                "name": "benefit_amount",
                "variable_name": "upstream_tax",
                "value_kind": "number",
                "module_identity": "upstream",
            }
        ]

    def test_load_rac_program_resolves_bare_imports_from_rac_toml(self, tmp_path):
        """Program loading can resolve bare imports through rac.toml module roots."""
        (tmp_path / "rac.toml").write_text(
            """
[module_resolution]
roots = ["./lib"]
"""
        )
        shared = tmp_path / "lib" / "tax" / "shared.rac"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text(
            """
export private_rate as rate

private_rate:
  source: "base-rate"
  from 2024-01-01: 0.1
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
from "tax/shared.rac" import rate

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=100)["tax"] == 10

    def test_load_rac_program_resolves_package_alias_imports(self, tmp_path):
        """Program loading resolves package-prefixed imports through rac.toml."""
        (tmp_path / "rac.toml").write_text(
            """
[module_resolution.packages]
tax = "./packages/tax"
"""
        )
        shared = tmp_path / "packages" / "tax" / "shared.rac"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text(
            """
export private_rate as rate

private_rate:
  source: "base-rate"
  from 2024-01-01: 0.1
"""
        )
        entry = tmp_path / "main.rac"
        entry.write_text(
            """
from "tax/shared.rac" import rate

tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * rate
"""
        )

        namespace = {}
        code = load_rac_program(entry).to_python_generator().generate()

        exec(code, namespace)

        assert namespace["calculate"](wages=100)["tax"] == 10
