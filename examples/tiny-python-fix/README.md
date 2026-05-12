# Tiny Python Fix

This is the smallest useful Goose acceptance demo: one intentionally broken
function and one failing test.

Task for Goose:

```text
Fix examples/tiny-python-fix/calculator.py so the validation command passes.
Keep the change minimal.
```

Validation command:

```bash
python -m unittest discover -s examples/tiny-python-fix -p "test_*.py"
```

Expected starting state:

- The command runs.
- The test fails because `add()` subtracts instead of adding.

Expected accepted state:

- `add(2, 3)` returns `5`.
- The validation command passes.
