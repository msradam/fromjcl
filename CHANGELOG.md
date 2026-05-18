# Changelog

## 0.3.0 (2026-05-18)

First public release on PyPI.

### Added

- Pure-Python JCL parser. Port of [Mike Fulton's JCLParser](https://github.com/MikeFultonDev/JCLParser).
- Foundational serializers: `to_json`, `to_yaml`, `to_csv`, `to_jcl`
  (byte-exact roundtrip), `to_raw` (parse-tree dump).
- Reverse path: `from_dump(text, fmt)` takes a JSON/YAML/CSV Job dump
  and emits functionally equivalent JCL.
- Typed model: `Job`, `Step`, `DD`, `Dataset`, `Disposition`, `Space`,
  `DCB` dataclasses with standard equality, `asdict()`, and structural
  pattern matching support.
- Typer-based CLI: `fromjcl job.jcl --to {json|yaml|csv|jcl|raw}`.
  Reverse with `--rejcl --from {json|yaml|csv}`. Reads stdin when
  input is omitted or `-`.
- Optional `[zoau]` extra: `--to zoau` and `--to mvscmd` translate
  steps into ZOAU 1.x shell. bashlex validates every flag against a
  frozen 55-verb / 493-flag manpage table; warnings prepend the
  script. Every emitted script carries an `EXPERIMENTAL` banner.
- IF/THEN/ELSE translator: JCL conditionals become bash
  `if (( ... )); then ... fi`. ABEND and RUN get best-effort
  approximations with explicit warning comments.

### Test corpus

83 JCL samples organised by source:

- `ibm/`: 47 verbatim Apache-2.0 samples from `github.com/IBM/*` and
  `github.com/zowe/*`, plus hand-authored paraphrases for parser
  constructs documented in IBM JCL Reference / DFSMS / MVS JCL User's
  Guide.
- `community/`: 8 from public blog posts and tutorials.
- `parser_edge_cases/`: 12 minimal samples targeting one parser
  quirk each.
- `zoau/`: 16 JCL files paired with `.zoau` oracle twins from IBM
  ZOAU 1.x topic pages. Drives `test_zoau_oracle.py`.

Every sample passes `parse(emit(parse(x))) == parse(x)` byte-for-byte
(`test_parser_roundtrip.py`). Real-world JCL also passes the
`Job -> {JSON,YAML,CSV} -> JCL -> Job` matrix
(`test_rejcl_matrix.py`).

### Build & release

- Pure-Python wheel. Installs under IBM Open Enterprise Python on
  z/OS as well as Linux, macOS, Windows.
- CI runs ruff format/check, mypy strict, vulture, pytest, bandit,
  pip-audit, twine check.
- Release workflow uses PyPI Trusted Publishing with PEP 740
  attestations.
