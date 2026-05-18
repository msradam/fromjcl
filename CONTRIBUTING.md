# Contributing to fromjcl

Thanks for your interest. fromjcl is Apache-2.0 and accepts
contributions via pull request.

## Developer Certificate of Origin (DCO)

Every commit must be signed off, certifying that you wrote the change
(or have the right to submit it) under the project's license:

```
git commit -s -m "your message"
```

This appends a `Signed-off-by:` line to the commit message. By doing so
you agree to the terms of the Developer Certificate of Origin v1.1
(<https://developercertificate.org/>).

## Pull request expectations

- Run `tests/check.sh` locally before pushing — it runs ruff format,
  ruff check, mypy (strict), vulture, and pytest. CI runs the same
  pipeline.
- For parser changes, add a JCL sample that exercises the case to
  `tests/jcl_samples/`. The byte-exact roundtrip matrix in
  `test_parser_roundtrip.py` will pick it up automatically.
- For ZOAU shell-emission changes, only update the frozen manpage
  table in `src/fromjcl/_zoau_flags.py` when you can cite the ZOAU
  release the new flags ship in.

## Test corpus additions

`tests/jcl_samples/` is organised by source:

- `ibm/` — verbatim Apache-2.0 samples from `github.com/IBM/IBM-Z-zOS`,
  plus hand-authored paraphrases that exercise constructs from IBM
  documentation. Both kinds must pass byte-exact roundtrip.
- `community/` — from blog posts and tutorials, credited per-file in
  `SOURCES.md`.
- `parser_edge_cases/` — minimal samples targeting one parser quirk
  each.
- `zoau/` — JCL paired with the canonical ZOAU command line IBM
  documents for the same operation; drives `test_zoau_oracle.py`.

When adding samples, update the relevant `SOURCES.md`.

## Reporting security issues

Please do not file public issues for security problems. See
[SECURITY.md](SECURITY.md).

## Code of conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
