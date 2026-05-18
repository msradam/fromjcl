# Changelog

## Unreleased

- Expand `tests/jcl_samples/ibm/` from 14 to 47 samples by pulling from
  github.com/IBM/* and zowe/* (Apache-2.0 / MIT only). New coverage now
  spans BCPii (`SYSAFF=`), CICS DFHCSDUP, DB2 utilities (`DSNTIAD`,
  IKJEFT01 + REXX), DBB COBOL/PL/I build flows, ICSF SORT+REXX,
  CustomPac SMP/E, Open Enterprise SDK for Apache Kafka, Z OS Client
  Web Enablement Toolkit, ansible-collections samples, RACF/SAF
  PassTicket setup (RDEFINE/PERMIT/SETROPTS/SSIGNON), CA-Top Secret
  equivalent, Z Open Editor sample ALLOCATE/PLIALLOC/ASMALLOC/REXALLOC/
  RUN/INCLUDE, multi-step PROC with PEND, and a long real-world job
  (db2ztools DSNTIJRS at 844 lines).
- Replace 9 IBM-Redbook-transcribed samples with hand-authored
  paraphrases that exercise the same parser constructs (continuation
  with `-`, nested IF/ELSE over PROC step refs, `JOB RESTART=` + IF
  with `¬` negation, `VOLUME=REF=` referbacks, full DISP variants,
  OUTPUT routing with `*.NAME` referbacks, ASM/LKED/GO with COND= and
  `PGM=*.LKED.SYSLMOD` referback). The "fair use" framing in
  `tests/jcl_samples/ibm/SOURCES.md` is gone — only Apache-2.0 / MIT
  GitHub samples and clean-room paraphrases ship now.
- Parser fixes surfaced by the expanded corpus:
  - **Bare `/*` end-of-data delimiters** between DD blocks (not after
    an in-stream DD) are now recognised as their own statement instead
    of being silently appended as a continuation record of the previous
    statement and re-emitted as `//`. Affects `_scanner.py` (new
    `_blank_after_prefix` dispatch path) and `serialize/jcl.py`
    (`_reconstruct_jes2` truncates to recorded record length).
  - **Trailing EBCDIC `\x1a` EOF sentinel** is stripped in
    `_records_from_bytes` instead of producing a spurious synthetic
    `//SYSIN DD *` to hold the byte. Source: PC-to-mainframe transfer
    convention.
  - **`INCLUDE` statements** now parse their `MEMBER=` parameter
    correctly. `INCLUDE` was missing from the `with_params` list in
    `_dispatch`, so the parameters were silently dropped.
  - **Multi-line `IF` conditions** continued across records (`OR\n
    cond`) now join with a space separator instead of concatenating
    `ORcond`. The serializer still emits the joined IF on one line
    (the multi-line IF re-emission gap is documented in
    `test_rejcl_matrix.py:_REJCL_XFAIL`).
- Instream-data serializer fixes:
  - Blank lines inside in-stream `DD *` blocks now survive the
    synthesis path (rejcl JCL emission). Previously a `if line:`
    filter in `serialize/jcl.py:_emit_dd_with_instream` dropped them.
  - The instream-cleanup in `serialize/__init__.py:remove_nulls`
    strips at most one terminating newline, so trailing blank lines
    (encoded as `\n\n`) survive the JSON/YAML/CSV roundtrip.
- Test count: 652 passing, 20 xfailed (all rejcl-matrix limitations:
  IF over 71 cols, CSV dropping job SET symbols, paren-list PARM
  over-escaping). Every sample passes byte-exact `parse → emit → parse`
  through `test_parser_roundtrip.py`.

## 0.3.0

- Add the `[zoau]` optional extra:
  - `--to zoau` translates each step into its closest ZOAU 1.x shell
    equivalent (dtouch, drm, dcp, dgrep, dsed, dzip/dunzip, dmv, mls,
    ...).
  - `--to mvscmd` emits the lower-level `mvscmd` / `mvscmdauth`
    invocation; falls back here for steps with no opinionated ZOAU
    mapping.
  - bashlex-based validator checks every flag in the emitted script
    against a frozen 55-verb / 493-flag ZOAU manpage table. Warnings
    surface as `# WARNING:` comments at the top of the script.
  - Every emitted shell script is marked `EXPERIMENTAL` in its header.
- Add IF/THEN/ELSE translation: JCL `IF (STEPx.RC = 0) THEN ... ELSE
  ... ENDIF` becomes `if (( step1_rc == 0 )); then ... fi`. `.ABEND` and
  `.RUN` get best-effort approximations with explicit warning comments.
- Add the rejcl roundtrip matrix test: JCL → {JSON, YAML, CSV} → JCL →
  Job IR must be a fixed point under dataclass equality, across the IBM
  / community / ZOAU corpora. Two known limitations are pinned as xfail
  with explicit reasons:
  - IF/THEN/ELSE re-emission can exceed JCL's 71-column line limit when
    rejcl reconstructs nested conditions as composite
    `(NOT A) AND (B)` strings. Affects `jcl_ref_if_nested.jcl` and
    `jcl_ug_asm_lked_go.jcl`. Fix lives in `serialize/jcl.py:_emit_if`.
  - CSV has no column for job-level SET symbols, so samples that
    declare symbols (`grs87.jcl`, `smf84fmt.jcl`) drop them on a CSV
    roundtrip. Fix is a design decision: add a column, emit a
    synthetic pre-row, or document.
- New corpus: `tests/jcl_samples/zoau/` (paired `.jcl` + `.zoau` files
  reproducing the canonical example for each ZOAU verb in the IBM topic
  pages) drives `test_zoau_oracle.py`.
- New corpus: `tests/jcl_samples/parser_edge_cases/` exercises inline
  DDs, OUTPUT statements, hex INCLUDE, PROC syntax, BPXBATCH coupledd.
- Expand `tests/jcl_samples/ibm/` from 14 to 19 samples by pulling from
  github.com/IBM/IBM-Z-zOS (Apache 2.0). New coverage: JES2 `/*JOBPARM`
  + `/*OUTPUT` referbacks, JES3 `/*SETUP` + `/*MESSAGE`, `JCLLIB ORDER=`,
  PROC step DD overrides (`//STEP.DDNAME`), multi-line `PARM.step=`
  overrides, BPXBATCH with inline `//STDPARM DD *` shell, sysplex
  `SYSTEM=`/`USER=` parameters. **The IBM/IBM-Z-zOS repo is JCL-poor
  (only 8 .jcl files in 1601)** — further corpus growth needs other
  upstream sources (IBM Redbooks, zopencommunity, IBM-Z-Samples).
- Known parser limitations surfaced by the expanded corpus (filed as
  TODOs in `src/fromjcl/_scanner.py`):
  - `/*` JES2/JES3 control statements drop column 73-80 sequence
    numbers. `//`/`//*` statements preserve them. Affected samples
    were saved with cols 73-80 blanked so byte-exact roundtrip still
    holds; the semantic content is verbatim. See
    `tests/jcl_samples/ibm/SOURCES.md` for the per-file note.
  - Trailing EBCDIC `\x1a` EOF bytes cause a spurious synthetic
    `//SYSIN DD *` to be appended on emit. Samples were saved with
    the trailing `\x1a` stripped.

## 0.2.0

- Initial public release. Parse z/OS JCL and serialize to JSON, YAML,
  CSV, raw parse-tree dump, or byte-exact roundtrip JCL.
