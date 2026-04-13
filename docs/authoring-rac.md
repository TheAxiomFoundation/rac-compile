# Authoring `.rac`

This guide is for writing RAC source files that compile cleanly through the
current `rac-compile` pipeline.

## File shape

A `.rac` file is made of:

- an optional top-level `source:` metadata block
- parameter definitions
- variable definitions
- optional imports / exports

Name modules by the subsection leaf they encode. Avoid generic entrypoint names
like `main.rac`.

The compiler uses that leaf name as the module/rule identity in merged graphs,
lowered bundles, and generated citation metadata. Within one loaded program,
those leaf identities must be unique.

For real policy work, author RAC as checked-in `.rac` files with rule citations
and source metadata in the file itself. Do not treat RAC as an ad hoc embedded
string format.

Shipped file example:

```rac
# /Users/maxghenis/TheAxiomFoundation/rac-compile/examples/simple_tax.rac

source:
  citation: "Example Tax Code"
  accessed: 2025-01-01

rate:
  source: "example/tax/rate"

tax:
  entity: Person
  period: Year
  dtype: Money
  label: "Income Tax"
  from 2025-01-01:
    return income * 0.2
```

The more representative policy examples are:

- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/eitc.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/ctc.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/snap.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/working_families/benefit_amount.rac`

## Parameters

Parameters are top-level names with either inline values or an external source.

Inline scalar parameter:

```rac
rate:
  source: "26 USC 1"
  values:
    0: 0.2
```

Indexed parameter table:

```rac
credit_pct:
  source: "26 USC 32(b)(1)"
  values:
    0: 7.65
    1: 34
    2: 40
    3: 45
```

Source-only parameter:

```rac
rate:
  source: "external/rate"
```

Source-only parameters must be bound explicitly at compile time with
`--parameter` or `--parameter-file`. For imported source-only parameters, use
`module_identity.symbol`.

## Variables

Variables are the compiled computations. They should include:

- `entity`
- `period`
- `dtype`
- one or more `from YYYY-MM-DD:` formula bodies

Real policy-style example:

```rac
# excerpted from /Users/maxghenis/TheAxiomFoundation/rac-compile/examples/eitc.rac

eitc:
  entity: TaxUnit
  period: Year
  dtype: Money
  label: "Earned Income Tax Credit"
  from 2025-01-01:
    n = min(n_children, 3)
    credit_pct_rate = credit_pct[n] / 100
    return round(max(0, earned_income * credit_pct_rate))
```

## Supported formula subset

The current compiler supports:

- assignments plus a final `return`
- arithmetic
- comparisons
- boolean operators
- ternaries like `cond ? a : b`
- indexed parameter access like `threshold[n]`
- `abs`, `ceil`, `floor`, `max`, `min`, `round`
- limited `if` / `elif` / `else` blocks when every reachable path returns

Example with statement-block branching:

```rac
tax:
  entity: Person
  period: Year
  dtype: Money
  from 2025-01-01:
    if is_joint:
      rate = 0.1
    else:
      rate = 0.2
    return wages * rate
```

The compiler fails loudly on unsupported constructs instead of guessing.

## Source connection

The source connection is part of the model, not optional decoration.

- top-level `source:` describes the file-level authority or archive context
- parameter `source:` fields tie values back to statutes, regulations, or guidance
- variable labels and citations define the public rule surface

If you are authoring real policy, prefer real `.rac` modules on disk over inline
snippets in host-language strings.

## Imports and exports

Local import:

```rac
import "./shared.rac"
```

Aliased import:

```rac
import "./shared.rac" as shared
```

Selective import:

```rac
from "./shared.rac" import rate_public as rate, taxable_income
```

Export public names:

```rac
export tax, taxable_income
export taxable_income as base_income
```

Re-export from another module:

```rac
export from "./shared.rac" import tax, rate as public_rate
```

## Bare imports

You can also import through configured module roots or package aliases:

```rac
from "tax/shared.rac" import rate
```

Those are resolved through:

- `rac.toml` `[module_resolution].roots`
- `rac.toml` `[module_resolution.packages]`
- CLI `--module-root`
- CLI `--package`

## Temporal definitions

Both parameters and variables can have multiple dated entries:

```rac
tax:
  entity: Person
  period: Year
  dtype: Money
  from 2024-01-01:
    return wages * 0.1
  from 2025-01-01:
    return wages * 0.2
```

Compile these with `--effective-date YYYY-MM-DD`.

## Good current patterns

- Use explicit `values:` blocks for inline numeric parameters.
- Keep formulas straight-line when possible.
- Use ternaries for simple expression-level branching.
- Use statement `if` blocks only when branch-local assignments make them clearer.
- Export only the public surface you want importers to depend on.
- Use `--select-output` to compile the smallest reachable subgraph.

## Current boundaries

The current generic compiler still does not support:

- loops
- `match` / `case`
- `try` / `except`
- arbitrary helper calls
- generic attribute access
- wildcard re-exports
- nested namespace chains beyond `alias.value`
- remote imports or package registries

For the exact supported scope, see the main README.
