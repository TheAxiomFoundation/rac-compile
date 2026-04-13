# Working Families Example Graph

This directory is the smallest shipped multi-file RAC example in the repo.

It demonstrates:

- leaf-named `.rac` modules
- selective imports
- import aliases
- re-exports
- exported output aliases
- qualified source-only external rule binding via `module_identity.symbol`

## Files

- `phase_in_rate.rac`: source-only external rule exported as `rate`
- `phase_in_cap.rac`: inline scalar parameter exported as `cap`
- `base_amount.rac`: imported helper variable exported as `base_amount`
- `benefit_amount.rac`: entry file that re-exports `base_amount` and publishes
  `benefit_amount`

## Compile

```bash
rac-compile compile examples/working_families/benefit_amount.rac \
  --python \
  --binding phase_in_rate.rate=0.25 \
  --select-output benefit_amount \
  -o benefit_amount.py
```

## Lower

```bash
rac-compile lower examples/working_families/benefit_amount.rac \
  --binding phase_in_rate.rate=0.25 \
  --select-output benefit_amount \
  -o benefit_amount.lowered.json
```

## Expected behavior

With `earned_income=4000` and `has_qualifying_child=true`, the selected public
output `benefit_amount` resolves to `1000`.
