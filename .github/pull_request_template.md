### Summary

(One or two sentences. Link any issue this closes.)

### Checklist

- [ ] `tests/check.sh` passes locally (ruff + mypy + vulture + pytest).
- [ ] If this changes parser or serializer behaviour, a JCL sample in
      `tests/jcl_samples/` covers the change.
- [ ] If this changes the public Python API (`fromjcl/__init__.py`
      exports), `tests/test_public_api.py` is updated.
- [ ] Commits are signed off (`git commit -s`); see [CONTRIBUTING.md](../CONTRIBUTING.md).
