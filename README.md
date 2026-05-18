# fromjcl

Parse IBM z/OS JCL into a typed Python model, then serialize it to
JSON, YAML, CSV, or back to byte-exact JCL.

![demo](docs/demo.gif)

```bash
fromjcl job.jcl --to json
fromjcl job.jcl --to yaml
fromjcl job.jcl --to csv          # one row per (step, DD, dataset)
fromjcl job.jcl --to jcl          # byte-exact roundtrip
fromjcl job.jcl --to raw          # parse-tree dump
```

The parser is a pure-Python port of [Mike Fulton's
JCLParser](https://github.com/MikeFultonDev/JCLParser) (Apache 2.0).
Byte-exact roundtrip is enforced on every commit against an 83-sample
corpus pulled from `github.com/IBM/*`, `github.com/zowe/*`, and
hand-authored paraphrases (see
[`tests/jcl_samples/`](tests/jcl_samples/)).

## Install

```bash
pip install fromjcl
```

Python 3.12+. Runtime deps are `pyyaml` and `typer`. Pure Python, so
the same wheel installs under IBM Open Enterprise Python on z/OS as
well as Linux, macOS, and Windows.

### Optional `[zoau]` extra (experimental)

```bash
pip install 'fromjcl[zoau]'
```

Enables `--to zoau` and `--to mvscmd`, which translate each step into
its closest ZOAU shell equivalent (or an `mvscmd`/`mvscmdauth`
invocation when no opinionated mapping exists). Pulls in
[bashlex](https://github.com/idank/bashlex) to structurally check
every flag in the emitted script against a frozen ZOAU 1.x manpage
table.

The output is best-effort. Every generated script starts with an
`EXPERIMENTAL` banner, and bashlex catches flag typos but does not
verify semantic equivalence to the source JCL. Review before running
against real datasets.

## Quick start

Given `test.jcl`:

```jcl
//TESTJOB  JOB (ACCT),'TEST',CLASS=A
//STEP01   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
 /* HELLO */
/*
```

`fromjcl test.jcl --to yaml`:

```yaml
name: TESTJOB
account: (ACCT)
programmer: TEST
class_: A
steps:
- name: STEP01
  program: IDCAMS
  dds:
  - name: SYSPRINT
    sysout: '*'
  - name: SYSIN
    instream: ' /* HELLO */'
```

## Querying with jq

```bash
# every dataset referenced
fromjcl job.jcl --to json | jq -r '.steps[].dds[].datasets[]?.dsn'

# datasets being created
fromjcl job.jcl --to json | jq -r '.steps[].dds[].datasets[]? | select(.disposition.status=="NEW") | .dsn'

# steps that run a specific program
fromjcl job.jcl --to json | jq -r '.steps[] | select(.program=="IDCAMS") | .name'
```

## Python API

The public surface is what `fromjcl/__init__.py` re-exports. Anything
under `fromjcl._*` or `fromjcl.converters.*` is internal.

```python
from fromjcl import parse, Job, to_yaml, to_jcl, from_dump

# Parse + walk the model.
job = Job.from_parsed(parse("test.jcl"))
for step in job.steps:
    print(step.name, step.program, [dd.name for dd in step.dds])

# Forward: serialize the Job to a human-readable format.
print(to_yaml(job))           # YAML
# to_json(job), to_csv(job) also available

# Byte-exact roundtrip preserves comments, column layout, blank lines.
# Pass the parse tree, not the Job (the Job IR is lossy by design).
print(to_jcl(parse("test.jcl")))

# Reverse: take a JSON/YAML/CSV dump and emit JCL (functionally
# equivalent, not byte-exact).
print(from_dump(open("job.yaml").read(), "yaml"))
```

Available names:

| Symbol | What it is |
| --- | --- |
| `parse(path)`, `parse_bytes(data)` | Parser. Returns a dict with full byte-level metadata. |
| `Job`, `Step`, `DD`, `Dataset`, `Disposition`, `Space`, `DCB` | Dataclasses. Standard equality, `asdict()`, structural pattern matching. |
| `Job.from_parsed(tree)` | Build the Job model from a parse tree. |
| `to_json(job)`, `to_yaml(job)`, `to_csv(job)` | Serialize a Job. |
| `to_jcl(tree)`, `to_raw(tree)` | Serialize a parse tree (byte-exact / raw dump). |
| `from_dump(text, fmt)` | Reverse path: text dump back to JCL. |

`[zoau]` extra adds two private modules accessible via the CLI's
`--to zoau` / `--to mvscmd` paths. They are not part of the stable
Python API.

## Reverse: re-emit JCL from JSON, YAML, or CSV

```bash
fromjcl job.json --rejcl              # auto-detects input format
fromjcl job.yaml --rejcl --from yaml
fromjcl job.csv  --rejcl --from csv
```

The reverse path produces *functionally equivalent* JCL, not
byte-exact. Comments, blank lines, and column layout are lost on the
forward pass through the IR and cannot be reconstructed. The
combinatoric matrix in [`tests/test_rejcl_matrix.py`](tests/test_rejcl_matrix.py)
asserts that `Job → format → JCL → Job` is a fixed point under
dataclass equality across the entire IBM/community/ZOAU corpus.

## z/OS notes

JCL input is read with standard z/OS UNIX semantics. If you hit a
silent decode failure, check the file tag (`ls -T`) and convert to
ASCII (`iconv -f IBM-1047 -t ISO8859-1`) before running.

If `pip install` itself trips over EBCDIC tagging, set
`_BPXK_AUTOCVT=ON` in the install shell.

## Development

```bash
uv sync --all-groups
tests/check.sh        # ruff format + check, mypy, vulture, pytest
```

The `test` group is z/OS-installable (pytest + bashlex, both pure
Python). The `dev` group adds workstation-only tooling (ruff, mypy,
vulture, radon, interrogate); ruff and uv are Rust binaries with no
z/OS build.

CI runs the same `tests/check.sh` pipeline on every push and pull
request (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): parser layout, IR
  shape, and the byte-exact roundtrip contract
- [CONTRIBUTING.md](CONTRIBUTING.md): DCO sign-off, PR expectations
- [SECURITY.md](SECURITY.md): private vulnerability reporting

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Trademarks

IBM, the IBM logo, z/OS, MVS, and Z Open Automation Utilities (ZOAU)
are trademarks or registered trademarks of International Business
Machines Corporation, registered in many jurisdictions worldwide.
Other product and service names might be trademarks of IBM or other
companies. A current list of IBM trademarks is available at
<https://www.ibm.com/legal/copytrade>.

This project is an independent community effort. It is not affiliated
with, endorsed by, or sponsored by IBM.
