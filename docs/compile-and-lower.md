# Compile And Lower

This guide covers the main `rac-compile` workflows.

## Compile to JavaScript, Python, or Rust

JavaScript:

```bash
rac-compile compile examples/simple_tax.rac -o simple_tax.js
```

Python:

```bash
rac-compile compile examples/snap.rac --python -o snap.py
```

Rust:

```bash
rac-compile compile examples/snap.rac --rust -o snap.rs
```

The generated calculators all come from the same lowered program bundle.

## Compile a file graph

Entry files can import other `.rac` files:

```bash
rac-compile compile examples/working_families/benefit_amount.rac --python -o benefit_amount.py
```

Use canonical RAC paths for real source trees rather than generic entrypoint
names. In other words, prefer `statute/26/32/c/2/A.rac` over `main.rac`.

The shipped file-graph example lives in:

- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/working_families/benefit_amount.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/working_families/base_amount.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/working_families/phase_in_rate.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/working_families/phase_in_cap.rac`

That example exercises import aliases, selective imports, re-exports, exported
output aliases, and qualified external rule binding.

There is a short companion note with runnable commands in:

- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/working_families/README.md`

You can also resolve bare imports through workspace roots:

```bash
rac-compile compile benefit_amount.rac --python --module-root ./lib -o benefit_amount.py
```

Or package aliases:

```bash
rac-compile compile benefit_amount.rac --python --package tax=./packages/tax -o benefit_amount.py
```

## Compile only selected public outputs

Use `--select-output` to prune the graph to the reachable subgraph for one output:

```bash
rac-compile compile examples/working_families/benefit_amount.rac --binding phase_in_rate.rate=0.25 --select-output benefit_amount --python -o benefit_amount.py
```

This works against the public output surface, including exported aliases.

## Temporal compilation

If a file has more than one dated definition, pass an effective date:

```bash
rac-compile compile policy.rac --effective-date 2025-01-01 --python -o policy.py
```

Without an effective date, the compiler errors instead of guessing.

## Bind external rules

One-off bindings:

```bash
rac-compile compile examples/working_families/base_amount.rac --binding phase_in_rate.rate=0.25 --python -o base_amount.py
rac-compile compile examples/working_families/benefit_amount.rac --binding phase_in_rate.rate=0.25 --select-output benefit_amount --python -o benefit_amount.py
```

Use `module_identity.symbol` when the bound rule lives in an imported file.
Bare names still work when they are unambiguous across the loaded graph.

JSON rule binding file:

```bash
rac-compile compile examples/working_families/benefit_amount.rac --binding-file bindings.json --python -o benefit_amount.py
```

Real RAC-side override artifact:

```bash
rac-compile compile examples/statute/26/32/b/2/A/base_amounts.rac \
  --binding-file ../rac-us/irs/rev-proc-2023-34/eitc-2024.yaml \
  --effective-date 2024-06-01 \
  --python -o base_amounts.py
```

Repeated `--binding-file` flags merge in order, and inline `--binding` flags
override file values.

Current boundary: override artifacts are supported for scalar values and
integer-indexed tables. Non-integer keyed artifacts still fail loudly.

## Emit the lowered bundle

Lowering stops after graph resolution, temporal resolution, external rule binding, and
selected-output pruning:

```bash
rac-compile lower examples/snap.rac -o snap.lowered.json
rac-compile lower examples/working_families/benefit_amount.rac --binding phase_in_rate.rate=0.25 --select-output benefit_amount -o benefit_amount.lowered.json
```

The lowered JSON includes:

- public inputs
- resolved external values, each with source and `module_identity`
- ordered computations, each with `module_identity`
- typed outputs, each with `module_identity`

When an input comes from an imported rule, its public lowered/runtime name is
`module_identity.symbol` rather than the compiler's merged internal helper name.
Generated Python/JS calculators accept those qualified names directly, and the
Rust output provides `calculate_public(...)` for the same public-input contract.

This is the backend-neutral seam between RAC source and target-specific codegen.
For canonical RAC trees, `module_identity` comes from the `statute/...`,
`regulation/...`, or `legislation/...` path. For ad hoc files outside those
roots, the compiler falls back to the file leaf.

## Python API

Real file-backed program:

```python
from datetime import date
from pathlib import Path
from rac_compile import load_rac_program

program = load_rac_program(Path("examples/eitc.rac"))

lowered = program.to_lowered_program(
    effective_date=date(2025, 1, 1),
    outputs=["eitc"],
)
python_code = lowered.to_python_generator().generate()
```

File graph:

```python
from datetime import date
from pathlib import Path
from rac_compile import load_rac_program

program = load_rac_program(Path("examples/working_families/benefit_amount.rac"))
rust_code = program.to_rust_generator(
    effective_date=date(2025, 1, 1),
    outputs=["benefit_amount"],
).generate()
```

For real policy assets, prefer loading `.rac` files from disk instead of
embedding RAC in Python strings. That keeps the rule source, citations, and
module graph visible at the source level.

## What to use when

- Use `compile` when you want runnable JS, Python, or Rust.
- Use `lower` when you want the resolved backend-neutral artifact.
- Use `--select-output` when you want a condensed subtree rather than the full graph.
- Use the Python API when you are embedding compilation inside another tool.

## Current boundaries

The current compile/lower surface still rejects unsupported constructs loudly.
The main README is the source of truth for the exact validated subset.
