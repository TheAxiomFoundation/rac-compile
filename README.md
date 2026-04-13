# rac-compile

Compile RAC `.rac` files to standalone JavaScript, Python, and Rust calculators.

## Overview

`rac-compile` generates JS, Python, and Rust code from RAC policy encodings. JavaScript output runs entirely in the browser with no server required. Python output can be imported and used in any Python application. Rust output is generated from the same lowered bundle for the current validated numeric/boolean generic subset. Every calculation includes a citation chain tracing values back to authoritative law.

## Installation

```bash
pip install rac-compile
```

## Guides

- `docs/compiler-architecture.md`: one-page architecture map, stability guide, and decision seams
- `docs/authoring-rac.md`: how to write `.rac` files, parameters, variables, imports, exports, and temporal definitions
- `docs/compile-and-lower.md`: CLI and Python API workflows for compile, lower, output selection, and parameter binding
- `docs/validation-and-oracles.md`: harness, validation modes, execution modes, and current oracle lanes

## Quick start

### Command line

```bash
# Generate JavaScript EITC calculator
rac-compile eitc -o eitc.js

# Generate Python EITC calculator
rac-compile eitc --python -o eitc.py

# Compile a RAC file to JavaScript
rac-compile compile examples/simple_tax.rac -o simple_tax.js

# Compile a RAC file to Python
rac-compile compile examples/snap.rac --python -o snap.py

# Compile a RAC file to Rust
rac-compile compile examples/snap.rac --rust -o snap.rs

# Compile a real RAC module and its local imports
rac-compile compile examples/working_families/benefit_amount.rac --python -o benefit_amount.py

# Compile with import aliases to disambiguate duplicate module symbols
rac-compile compile examples/working_families/benefit_amount.rac --python -o benefit_amount.py
# where benefit_amount.rac contains lines like: import "./base_amount.rac" as base

# Compile using explicit exports plus selective imports
rac-compile compile examples/working_families/base_amount.rac --python -o base_amount.py
# where base_amount.rac contains lines like:
# from "./phase_in_rate.rac" import rate

# Compile with aliased public outputs
rac-compile compile examples/working_families/benefit_amount.rac --python -o benefit_amount.py
# where benefit_amount.rac contains lines like: export benefit as benefit_amount
# and --select-output uses the public name benefit_amount

# Re-export an imported symbol into a new public module surface
rac-compile compile examples/working_families/benefit_amount.rac --python -o benefit_amount.py
# where benefit_amount.rac contains lines like:
# export from "./base_amount.rac" import base_amount

# Resolve bare imports through workspace module roots
rac-compile compile benefit_amount.rac --python --module-root ./lib -o benefit_amount.py
# or configure rac.toml:
# [module_resolution]
# roots = ["./lib"]

# Resolve stable package-prefixed imports through workspace package aliases
rac-compile compile benefit_amount.rac --python --package tax=./packages/tax -o benefit_amount.py
# or configure rac.toml:
# [module_resolution.packages]
# tax = "./packages/tax"

# Compile only the subgraph needed for one output
rac-compile compile examples/working_families/benefit_amount.rac --parameter phase_in_rate.rate=0.25 --select-output benefit_amount --python -o benefit_amount.py

# Emit the lowered selected-output bundle as JSON
rac-compile lower examples/working_families/benefit_amount.rac --parameter phase_in_rate.rate=0.25 --select-output benefit_amount -o benefit_amount.lowered.json

# Run the built-in compiler, batch-execution, and example-oracle scorecard
rac-compile harness

# Opt into curated compatibility checks against sibling live-stack RAC files
# and AutoRAC artifacts
rac-compile harness --include-live

# Opt into external PolicyEngine-backed oracle checks (requires policyengine-us)
rac-compile harness --include-external

# Resolve temporal unified .rac definitions for a specific date
rac-compile compile examples/snap.rac --effective-date 2025-01-01 --python -o snap.py

# Bind a source-only parameter reference at compile time
rac-compile compile examples/working_families/base_amount.rac --parameter phase_in_rate.rate=0.25 --python -o base_amount.py
# or, for imported source-only parameters, bind by rule identity:
rac-compile compile examples/working_families/benefit_amount.rac --parameter phase_in_rate.rate=0.25 --python -o benefit_amount.py

# Load parameter bindings from a JSON file
rac-compile compile examples/working_families/benefit_amount.rac --parameter-file bindings.json --python -o benefit_amount.py

# Output to stdout
rac-compile eitc           # JavaScript
rac-compile eitc --python  # Python
```

### Python API

```python
from datetime import date
from pathlib import Path
from rac_compile import (
    generate_eitc_calculator_js,
    generate_eitc_calculator_py,
    load_rac_program,
)

# Pre-built EITC calculator (JavaScript)
js_code = generate_eitc_calculator_js()
print(js_code)

# Pre-built EITC calculator (Python)
py_code = generate_eitc_calculator_py()
print(py_code)

# Load and compile a real source-anchored RAC file
program = load_rac_program(Path("examples/eitc.rac"))

python_code = program.to_python_generator(
    effective_date=date(2025, 1, 1),
    outputs=["eitc"],
).generate()

lowered_json = program.to_lowered_program(
    effective_date=date(2025, 1, 1),
    outputs=["eitc"],
).to_json()

rust_code = program.to_rust_generator(
    effective_date=date(2025, 1, 1),
    outputs=["eitc"],
).generate()
```

For real policy work, keep RAC in `.rac` files with `source:` metadata and cited
parameter / variable sources. The public docs prefer file-backed examples over
inline RAC strings for that reason.

### Generated output

```javascript
const PARAMS = {
  credit_pct: { 0: 7.65, 1: 34, 2: 40, 3: 45 },  // 26 USC 32(b)(1)
  // ...
};

function calculate({ earned_income = 0, agi = 0, n_children = 0, is_joint = false }) {
  const eitc = /* formula */;

  return {
    eitc,
    citations: [
      {
        param: "credit_pct",
        module_identity: "eitc",
        source: "26 USC 32(b)(1)"
      },
      { variable: "eitc", module_identity: "eitc", source: "26 USC 32" },
    ],
  };
}

export { calculate, PARAMS };
export default calculate;
```

## Features

- **Multi-target compilation**: Generate JavaScript, Python, or Rust from the same DSL
- **Citation chains**: Every calculation traces back to statute/guidance
- **Zero dependencies**: Generated code runs standalone (JS in browsers, Python anywhere)
- **ESM exports**: JavaScript works with modern bundlers and `<script type="module">`
- **Type hints**: Python output includes full type annotations, TypeScript support coming soon

## Generic Compile Scope

The generic `rac-compile compile` path now shares one parsed compile model for JavaScript, Python, and Rust.

- Supported: straight-line formulas with assignments plus a final `return`
- Supported: scalar expressions built from arithmetic, comparisons, boolean operators, ternaries, indexed parameter access, inline RAC conditionals like `if cond: a else: b`, and `abs` / `ceil` / `floor` / `max` / `min` / `round`
- Supported: limited `if` / `elif` / `else` formula blocks when every reachable path returns a value
- Supported: parameter references discovered from parsed formulas, with free references exposed as calculator inputs
- Supported: inline numeric parameter values from `.rac` `values:` blocks and single-entry temporal `.rac` parameters, with exact integer-vs-number kinds preserved in the lowered bundle
- Supported: multi-entry temporal unified `.rac` parameters and formulas when `--effective-date` is provided
- Supported: source-only parameters when you bind them explicitly with `--parameter NAME=VALUE`, `--parameter module_identity.symbol=VALUE`, or indexed variants
- Supported: source-only parameters from a JSON `--parameter-file`, with inline `--parameter` flags overriding file values
- Supported: explicit scalar-vs-indexed parameter lookup contracts in the lowered bundle, with bare parameter references validated against resolved parameter shape
- Supported: output-focused compilation via repeated `--select-output NAME`, pruning to the reachable variable subgraph for those outputs
- Supported: lowered bundle emission via `rac-compile lower`, producing a serializable post-resolution artifact with explicit inputs, typed parameters, typed ordered computations, and typed public outputs
- Supported: Rust output via `rac-compile compile ... --rust`, using the same lowered bundle as JS/Python for the validated numeric/boolean subset
- Supported: local file imports written as `import "./shared.rac"` or `import "../common/base.rac"`, with graph-wide reachability pruning from the selected outputs
- Supported: bare imports like `from "tax/shared.rac" import rate` when resolved through `rac.toml` module roots or repeated `--module-root DIR`
- Supported: stable workspace package aliases through `rac.toml` `[module_resolution.packages]` or repeated `--package NAME=DIR`
- Supported: import aliases written as `import "./shared.rac" as shared`, with module-qualified references like `shared.rate`
- Supported: explicit module exports via `export tax, taxable_income`
- Supported: export aliases via `export taxable_income as base_income`
- Supported: module re-exports via `export from "./shared.rac" import tax, rate as public_rate`
- Supported: selective imports via `from "./shared.rac" import tax, threshold as income_threshold`
- Supported: entry-file output selection against the public export surface, including aliased output names
- Supported: first-class rule/module identity preserved through lowered bundles and generated citations; canonical `statute/...`, `regulation/...`, and `legislation/...` files use their path identity
- Unsupported: package registries, remote imports, nested namespace chains beyond `alias.value`, wildcard re-exports, loops, match/case, try/except, and other statement forms outside assignments, `if` / `elif` / `else`, and `return`
- Unsupported: attribute access, custom helper calls, slices, and other expression forms outside the validated scalar subset
- Unsupported: string formula literals in Rust output, and the prebuilt `rac-compile eitc` shortcut still only emits JavaScript or Python

If a file has multiple temporal entries and you do not supply an effective date, the compiler errors instead of guessing.
If a referenced parameter has no inline numeric values and you do not bind it explicitly, the compiler errors instead of inventing a placeholder.
If a bare parameter reference resolves to multiple indexed values, the compiler errors instead of silently taking index `0`.
If a control-flow formula does not return a value on every reachable path, the compiler errors instead of emitting `None` / `undefined`.
If plain imports expose the same symbol name more than once, the compiler errors instead of guessing which one you meant.
If a selective import asks for a name a module does not export, the compiler errors instead of treating it as an input.
If a file defines explicit exports, output selection and generated result keys use those public names instead of hidden internal helper names.
If a re-export asks for a name a dependency does not export, the compiler errors instead of silently omitting it.
If a bare import has no configured module root, or resolves to more than one file across roots, the compiler errors instead of guessing.
If a package-prefixed import names an unknown package alias, or a configured package alias points at no file, the compiler errors instead of falling back to a different root.
If a loaded program contains two different `.rac` files with the same canonical rule identity, the compiler errors instead of inventing an ambiguous identity.
If a bare parameter binding name matches more than one imported source-only parameter, the compiler errors instead of guessing; bind it as `module_identity.symbol`.

Unsupported constructs fail with an explicit compiler error instead of generating misleading output.

### Lowered Bundle

`rac-compile lower` emits the compiler's backend-neutral bundle after import resolution,
temporal resolution, parameter binding, and selected-output pruning. The JSON payload
includes:

- explicit public inputs
- resolved parameter values and sources, each with an explicit `value_kind` plus `lookup_kind` metadata, `index_value_kind` for indexed tables, and the originating file's `module_identity`
- topologically ordered computations expressed in validated statement/expression IR, each with an explicit `value_kind`, typed local slot metadata, and `module_identity`
- public outputs mapped to the internal computation names they expose, each with an explicit `value_kind` and `module_identity`

JS, Python, and Rust generation now consume that same lowered bundle internally,
so the artifact is the exact seam between graph compilation and target-specific
rendering.

### Parameter Bundle Format

`--parameter-file` accepts either a simple compatibility map:

```json
{
  "rate": 0.25,
  "shared.rate": 0.3,
  "thresholds": [10000, 20000, 30000]
}
```

Or a structured bundle with schema/versioning and parameter metadata:

```json
{
  "schema_version": 1,
  "metadata": {
    "name": "TY2025 external parameters"
  },
  "parameters": {
    "rate": {
      "value": 0.25,
      "source": "bundle://ty2025",
      "unit": "rate"
    },
    "thresholds": {
      "values": {
        "0": 10000,
        "1": 20000,
        "2": 30000
      },
      "source": "bundle://ty2025"
    }
  }
}
```

If a JSON file is ambiguous between the structured bundle form and a plain
parameter map, `rac-compile` now errors instead of guessing. In practice, that
means schema-versioned bundles with unusual numeric parameter names should also
include a dict-valued `metadata` object to make the intent explicit.

### Compiler Harness

`rac-compile harness` runs a built-in scorecard of named compiler cases across the
current supported subset. It is intended to give future compiler work an explicit
objective target: improve the harness score by adding support, or add a new
failing case first and then make it pass.

- Use `rac-compile harness` for the human-readable scorecard
- Use `rac-compile harness --json` for machine-readable output
- Use repeated `--case NAME` to run a focused subset while developing a feature
- The harness now also validates Rust when `rustc` is available locally
- `rac-compile harness --include-live` opts into curated real-file compatibility checks against sibling repos such as `rac-us` and current AutoRAC artifacts
- `rac-compile harness --include-external` opts into PolicyEngine-backed oracle cases when `policyengine-us` is installed

### Validation

`rac-validate --mode sample` now runs the shipped compiled `.rac` examples in the
per-household RAC lane before comparing them to PolicyEngine. The full vectorized
validation path now uses the lowered-program batch executor for the current
validated lowered subset, including limited `if` / `elif` / `else` statement
blocks, instead of the old handwritten RAC formulas.
Validation reports label the current modes explicitly as
`compiled_example` for per-household sample validation and `compiled_batch`
for the full batch path.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=rac_compile
```

## See also

- [Rules Foundation](https://rules.foundation) - Open infrastructure for encoded law
- [pe-compile](https://github.com/PolicyEngine/pe-compile) - Similar tool for PolicyEngine
