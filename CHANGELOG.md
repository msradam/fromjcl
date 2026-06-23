# Changelog

## 0.5.0 (2026-06-23)

### Added

- **EBCDIC input support.** `parse()` and `parse_bytes()` now accept an
  `encoding` parameter (`"auto"` | `"ebcdic"` | `"cp037"` | `"cp500"` |
  `"cp1047"`). Auto-detection checks for the EBCDIC `//` file signature
  (bytes `0x61 0x61`) and decodes with cp037 by default, handling both
  variable-length (NL-separated) and fixed 80-byte records. `cp1047` is
  accepted as an alias for cp037 (JCL characters are identical in both
  code pages). The CLI gains a matching `--encoding` flag. The z/OS
  `iconv` pre-processing step is no longer required for binary-transferred
  JCL.
- **`DD.instream_dlm`** field on the `DD` model: custom `DLM=` delimiters
  are now preserved through the forward pass. JSON, YAML, and CSV
  serialisers include the value; the rejcl reverse path emits `DATA,DLM='XX'`
  and uses the custom terminator when reconstructing JCL.
- Python 3.13 classifier and CI test matrix entry.

### Fixed

- **Scanner: JES2/3 cols 73-80 sequence numbers** on `/*` control statements
  (e.g., `/*JOBPARM`, `/*SETUP`) were dropped during roundtrip. The scanner
  now captures the tail, matching the `//` and `//*` behaviour.
- **CLI: empty or comment-only JCL** now emits a warning to stderr with a
  preview of the input (up to 5 lines) and exits 0 rather than silently
  producing empty output.
- **CLI: bare Python tracebacks** from I/O errors, bad paths, and serialiser
  failures now surface as clean `fromjcl: <reason>` messages on stderr.

## 0.4.0 (2026-05-23)

### Added

- Syntax-highlighted terminal output via Rich. `--to json`, `--to yaml`,
  `--to jcl`, `--to zoau`, and `--to mvscmd` colorize output when stdout
  is a TTY (monokai theme); piped output is plain text, byte-for-byte
  identical to file output (`-o`).

### Fixed

- **Scanner: false-positive continuation state** on lines where content
  reaches column 72 (e.g., template JOB cards with long `MSGCLASS=`
  values). The scanner incorrectly set `ContinueComment` state, causing
  the next statement to fail with `Invalid continued comment record`.
- **Scanner: lowercase jobname rejection.** Jobnames with lowercase
  characters (common in template JCL, e.g., `TKTxxx1`) were rejected as
  invalid. Name-character validation now accepts any ASCII letter.
- **Scanner: multi-element JOB account truncation.** Account fields of
  the form `(B004273,BIN#,BLDG#,DEPT#)` were split at the first comma
  inside the parentheses. Paren-nesting is now tracked in the keyword
  context so the full group is preserved.
- **CLI: invalid JSON when piping `--to json`** on JCL with instream
  data. Rich's Pygments JSON lexer was expanding `\n` escape sequences
  to literal newlines inside string values. Syntax highlighting now
  activates only for interactive terminals.

## 0.3.1 (2026-05-18)

### Fixed

- README demo gif now uses an absolute `raw.githubusercontent.com` URL
  so PyPI's project page renders it. Relative paths only resolve on
  GitHub itself.

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
