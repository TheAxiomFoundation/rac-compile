# Validation And Oracles

`rac-compile` now has two validation layers:

- the compiler harness
- the RAC vs PolicyEngine validation pipeline

They are related, but they solve different problems.

## 1. Compiler harness

Run the built-in scorecard:

```bash
rac-compile harness
rac-compile harness --json
```

The harness is the fast objective loop for compiler work. It checks:

- generic compile features
- graph/import/export behavior
- lowered bundle consistency
- generated runtime behavior
- batch execution
- shipped example oracles

Opt into curated live-stack compatibility checks against sibling repos and
artifacts such as `rac-us`, `rac-us-co`, and `autorac`:

```bash
rac-compile harness --include-live
```

Focused runs:

```bash
rac-compile harness --case branching_formula
rac-compile harness --case branching_batch_execution
rac-compile harness --case oracle_snap_example
```

External oracle cases are opt-in:

```bash
rac-compile harness --include-external
```

That currently enables PolicyEngine-backed checks when `policyengine-us` is
installed.

## 2. Validation pipeline

Run per-household sample validation:

```bash
rac-validate --mode sample
```

Run the full CPS/vectorized lane:

```bash
rac-validate --mode full
```

## Current execution modes

Reports now label which RAC execution path produced the result:

- `compiled_example`: compiled `.rac` example calculators on one household at a time
- `compiled_batch`: lowered-program batch execution over a full DataFrame
- `policyengine_household`: one-household PolicyEngine evaluation
- `policyengine_microsim`: PolicyEngine microsimulation over CPS data

## What is being compared

Today, the shipped policy examples are:

- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/eitc.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/ctc.rac`
- `/Users/maxghenis/TheAxiomFoundation/rac-compile/examples/snap.rac`

The harness compares compiled outputs from those files against Python reference
calculators. The external harness lane can also compare compiled SNAP output to a
PolicyEngine household oracle.

The validation pipeline compares RAC-side results to PolicyEngine at a larger
scale, including the full CPS/microsim path.

## When to use which tool

- Use `rac-compile harness` while changing the compiler itself.
- Use `rac-validate --mode sample` for quick behavior checks against PolicyEngine.
- Use `rac-validate --mode full` for broader empirical comparison on CPS data.

## Current boundaries

- External PolicyEngine harness cases are optional and depend on local install.
- The batch executor supports the current validated lowered subset, including
  limited `if` / `elif` / `else` blocks.
- Unsupported lowered constructs still fail loudly rather than degrading into
  approximate validation.

## Practical workflow

Typical compiler iteration loop:

1. Add or update a harness case.
2. Make the compiler pass it.
3. Run `rac-compile harness`.
4. Run `rac-validate --mode sample` if the change affects shipped examples.
5. Run `rac-validate --mode full` for bigger validation changes.
