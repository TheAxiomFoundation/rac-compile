"""
Python code generation from RAC DSL.

Generates standalone Python calculators that can be imported
and used in Python applications without any dependencies.
"""

import ast
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Parameter:
    """A parameter value from statute or guidance."""

    name: str
    values: dict[int, float]  # key by number of children or bracket index
    source: str  # e.g., "26 USC 32(b)(1)" or "Rev. Proc. 2024-40"
    module_identity: str = ""


@dataclass
class Variable:
    """A compiled variable ready for Python generation."""

    name: str
    inputs: list[str]
    formula_python: str
    label: str = ""
    citation: str = ""
    module_identity: str = ""


@dataclass
class Output:
    """A public output exposed by the generated calculator."""

    name: str
    variable_name: str


class PythonCodeGenerator:
    """
    Generate standalone Python calculators from RAC DSL.

    Usage:
        gen = PythonCodeGenerator()
        gen.add_parameter("credit_pct", {0: 7.65, 1: 34, ...}, "26 USC 32(b)(1)")
        gen.add_variable("eitc", ["earned_income", "agi", ...], formula_python)
        code = gen.generate()
    """

    def __init__(
        self,
        module_name: str = "calculator",
        include_provenance: bool = True,
        type_hints: bool = True,
    ):
        self.module_name = module_name
        self.include_provenance = include_provenance
        self.type_hints = type_hints
        self.parameters: dict[str, Parameter] = {}
        self.variables: list[Variable] = []
        self.outputs: list[Output] | None = None
        self.inputs: dict[str, Any] = {}  # name -> default value

    def add_input(self, name: str, default: Any = 0, type_hint: str = "float") -> None:
        """Add an input variable."""
        self.inputs[name] = {"default": default, "type": type_hint}

    def add_parameter(
        self,
        name: str,
        values: dict[int, float],
        source: str = "",
        module_identity: str = "",
    ) -> None:
        """Add a parameter with values indexed by bracket."""
        self.parameters[name] = Parameter(
            name=name,
            values=values,
            source=source,
            module_identity=module_identity,
        )

    def add_variable(
        self,
        name: str,
        inputs: list[str],
        formula_python: str,
        label: str = "",
        citation: str = "",
        module_identity: str = "",
    ) -> None:
        """Add a calculated variable with its Python formula."""
        self.variables.append(
            Variable(
                name=name,
                inputs=inputs,
                formula_python=formula_python,
                label=label,
                citation=citation,
                module_identity=module_identity,
            )
        )

    def set_outputs(self, output_names: list[Any]) -> None:
        """Set the public outputs returned by calculate()."""
        self.outputs = self._normalize_outputs(output_names)

    def generate(self) -> str:
        """Generate the complete Python module."""
        lines = []

        # Header with provenance
        lines.append('"""')
        lines.append(f"{self.module_name} - Auto-generated from RAC DSL")
        lines.append("")
        lines.append("This code runs standalone with full citation chain -")
        lines.append("every value traces back to authoritative law.")

        if self.include_provenance:
            lines.append("")
            lines.append("Sources:")
            sources = set()
            for param in self.parameters.values():
                if param.source:
                    sources.add(param.source)
            for output, var in self._resolved_outputs():
                if var.citation:
                    sources.add(var.citation)
            for src in sorted(sources):
                lines.append(f"  - {src}")
        lines.append('"""')
        lines.append("")

        # Type imports if needed
        if any("math." in var.formula_python for var in self.variables):
            lines.append("import math")
        if (
            any("math." in var.formula_python for var in self.variables)
            and self.type_hints
        ):
            lines.append("")
        if self.type_hints:
            lines.append("from typing import Any")
            lines.append("")

        # Parameters as constant dict
        if self.parameters:
            lines.append("# Parameters from statute and guidance")
            lines.append("PARAMS = {")
            for param in self.parameters.values():
                values_str = (
                    "{"
                    + ", ".join(f"{k}: {v}" for k, v in sorted(param.values.items()))
                    + "}"
                )
                comment = f"  # {param.source}" if param.source else ""
                lines.append(f'    "{param.name}": {values_str},{comment}')
            lines.append("}")
            lines.append("")
        else:
            lines.append("PARAMS = {}")
            lines.append("")

        # Main calculate function
        self._generate_function(lines)

        return "\n".join(lines)

    def _generate_function(self, lines: list[str]) -> None:
        """Generate Python function."""
        # Function signature
        if self.type_hints:
            # Build parameter list with type hints
            params = []
            for name, info in self.inputs.items():
                type_str = info["type"]
                default = info["default"]
                if isinstance(default, bool):
                    default_str = str(default)
                elif isinstance(default, str):
                    default_str = f'"{default}"'
                else:
                    default_str = str(default)
                params.append(f"{name}: {type_str} = {default_str}")

            params_str = ", ".join(params) if params else ""
            lines.append(f"def calculate({params_str}) -> dict[str, Any]:")
        else:
            # No type hints
            params = []
            for name, info in self.inputs.items():
                default = info["default"]
                if isinstance(default, bool):
                    default_str = str(default)
                elif isinstance(default, str):
                    default_str = f'"{default}"'
                else:
                    default_str = str(default)
                params.append(f"{name}={default_str}")

            params_str = ", ".join(params) if params else ""
            lines.append(f"def calculate({params_str}):")

        # Docstring
        lines.append('    """')
        lines.append("    Calculate tax/benefit values with full citation chain.")
        lines.append("")
        for name, info in self.inputs.items():
            lines.append("    Args:")
            break
        for name, info in self.inputs.items():
            lines.append(f"        {name}: {info['type']}")
        lines.append("")
        lines.append("    Returns:")
        lines.append("        Dictionary with calculated values and citations")
        lines.append('    """')

        # Add calculations
        for var in self.variables:
            if var.citation:
                lines.append(f"    # {var.citation}")
            if self._is_block_formula(var.formula_python):
                helper_name = f"_calculate_{var.name}"
                lines.append(f"    def {helper_name}():")
                for formula_line in self._normalize_block_formula_python(
                    var.formula_python
                ):
                    lines.append(f"        {formula_line}")
                lines.append(f"    {var.name} = {helper_name}()")
            else:
                lines.append(f"    {var.name} = {var.formula_python}")
            lines.append("")

        # Return dictionary with citations
        lines.append("    return {")
        for output, _ in self._resolved_outputs():
            lines.append(
                f'        "{output.name}": {output.variable_name},'
            )
        lines.append('        "citations": [')
        for param in self.parameters.values():
            if param.source:
                lines.append(
                    f'            {{"param": "{param.name}",'
                    f' "module_identity": "{param.module_identity}",'
                    f' "source": "{param.source}"}},'
                )
        for output, var in self._resolved_outputs():
            if var.citation:
                lines.append(
                    f'            {{"variable": "{output.name}",'
                    f' "module_identity": "{var.module_identity}",'
                    f' "source": "{var.citation}"}},'
                )
        lines.append("        ],")
        lines.append("    }")

    def _is_block_formula(self, formula_python: str) -> bool:
        """Return whether the formula must be emitted as a statement block."""
        stripped = formula_python.strip()
        if not stripped:
            return False

        try:
            ast.parse(stripped, mode="eval")
        except SyntaxError:
            return True
        return False

    def _normalize_block_formula_python(self, formula_python: str) -> list[str]:
        """Ensure a Python statement block returns its final expression explicitly."""
        lines = self._split_inline_python_statements(formula_python)
        last_index = self._last_nonempty_line(lines)
        if last_index is None:
            raise ValueError("Python block formulas cannot be empty.")

        stripped = lines[last_index].strip()
        if self._is_return_statement_python(stripped):
            return lines
        if self._is_expression_line_python(stripped):
            indent = lines[last_index][
                : len(lines[last_index]) - len(lines[last_index].lstrip())
            ]
            lines[last_index] = f"{indent}return {stripped}"
            return lines
        raise ValueError(
            "Python block formulas must end with an explicit return "
            "or a final expression."
        )

    def _is_expression_line_python(self, line: str) -> bool:
        """Return whether a Python line can be treated as a final expression."""
        try:
            ast.parse(line, mode="eval")
        except SyntaxError:
            return False
        return True

    def _last_nonempty_line(self, lines: list[str]) -> int | None:
        """Return the index of the last non-empty line in a block."""
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].strip():
                return index
        return None

    def _is_return_statement_python(self, line: str) -> bool:
        """Return whether a Python line starts with a return statement."""
        return bool(re.match(r"return\b", line))

    def _split_inline_python_statements(self, formula_python: str) -> list[str]:
        """Split same-line Python statements on semicolons outside string literals."""
        lines: list[str] = []
        for raw_line in formula_python.splitlines():
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]
            content = raw_line[len(indent) :]
            current: list[str] = []
            quote: str | None = None
            escaped = False
            for char in content:
                if quote is not None:
                    current.append(char)
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == quote:
                        quote = None
                    continue
                if char in {"'", '"'}:
                    quote = char
                    current.append(char)
                    continue
                if char == ";":
                    statement = "".join(current).strip()
                    if statement:
                        lines.append(f"{indent}{statement}")
                    current = []
                    continue
                current.append(char)
            statement = "".join(current).strip()
            if statement:
                lines.append(f"{indent}{statement}")
            elif not lines or lines[-1].strip():
                lines.append("")
        return lines

    def _normalize_outputs(self, output_names: list[Any]) -> list[Output]:
        """Normalize output bindings from strings or output-like objects."""
        outputs: list[Output] = []
        seen_public_names: set[str] = set()

        for output_name in output_names:
            if isinstance(output_name, str):
                output = Output(name=output_name, variable_name=output_name)
            else:
                public_name = getattr(output_name, "name")
                variable_name = getattr(output_name, "variable_name", public_name)
                output = Output(name=public_name, variable_name=variable_name)
            if output.name in seen_public_names:
                continue
            seen_public_names.add(output.name)
            outputs.append(output)
        return outputs

    def _resolved_outputs(self) -> list[tuple[Output, Variable]]:
        """Return the public outputs paired with their backing variables."""
        if self.outputs is None:
            return [
                (
                    Output(name=variable.name, variable_name=variable.name),
                    variable,
                )
                for variable in self.variables
            ]
        variables_by_name = {variable.name: variable for variable in self.variables}
        return [
            (output, variables_by_name[output.variable_name]) for output in self.outputs
        ]


def generate_eitc_calculator(tax_year: int = 2025) -> str:
    """
    Generate a standalone EITC calculator for the specified tax year.

    This is a pre-built calculator based on 26 USC 32.
    """
    gen = PythonCodeGenerator(module_name=f"EITC Calculator (TY {tax_year})")

    # Inputs
    gen.add_input("earned_income", 0, "float")
    gen.add_input("agi", 0, "float")
    gen.add_input("n_children", 0, "int")
    gen.add_input("is_joint", False, "bool")

    # Parameters from statute (fixed percentages)
    gen.add_parameter(
        "credit_pct",
        {0: 7.65, 1: 34, 2: 40, 3: 45},
        "26 USC 32(b)(1)",
    )
    gen.add_parameter(
        "phaseout_pct",
        {0: 7.65, 1: 15.98, 2: 21.06, 3: 21.06},
        "26 USC 32(b)(1)",
    )

    # Parameters from IRS guidance (inflation-adjusted for TY 2025)
    gen.add_parameter(
        "earned_income_amount",
        {0: 8260, 1: 12730, 2: 17880, 3: 17880},
        "Rev. Proc. 2024-40",
    )
    gen.add_parameter(
        "phaseout_single",
        {0: 10620, 1: 23350, 2: 23350, 3: 23350},
        "Rev. Proc. 2024-40",
    )
    gen.add_parameter(
        "phaseout_joint",
        {0: 17730, 1: 30470, 2: 30470, 3: 30470},
        "Rev. Proc. 2024-40",
    )

    # EITC formula - follows 26 USC 32(a)

    # Simpler, more readable version
    eitc_formula_simple = """(lambda n: (
    lambda credit_base, income_for_phaseout, phaseout_start, phaseout_pct:
        max(0, round(
            credit_base - phaseout_pct
            * max(0, income_for_phaseout - phaseout_start)
        ))
    )(
        PARAMS['credit_pct'][n] / 100
        * min(earned_income, PARAMS['earned_income_amount'][n]),
        max(agi, earned_income),
        PARAMS['phaseout_joint'][n] if is_joint else PARAMS['phaseout_single'][n],
        PARAMS['phaseout_pct'][n] / 100
    )
)(min(n_children, 3))"""

    gen.add_variable(
        "eitc",
        ["earned_income", "agi", "n_children", "is_joint"],
        eitc_formula_simple,
        label="Earned Income Tax Credit",
        citation="26 USC 32",
    )

    return gen.generate()


if __name__ == "__main__":
    # Generate and print EITC calculator
    print(generate_eitc_calculator())
