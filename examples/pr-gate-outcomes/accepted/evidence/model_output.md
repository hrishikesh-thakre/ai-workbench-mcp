# Synthetic Captured Output

Status: response_captured

Summary:
- Updated documentation-only example text.
- Reported that deterministic validation completed.
- No provider transcript, token log, or private path is included in this fixture.

Validation:
- `python -m pytest tests/test_examples.py -q -p no:cacheprovider` passed.
