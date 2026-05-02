# fromjcl

Parse IBM z/OS JCL and serialize it to JSON, YAML, CSV, or roundtrip
back to JCL.

```bash
fromjcl job.jcl --to json
fromjcl job.jcl --to yaml
fromjcl job.jcl --to csv          # one row per (step, DD, dataset)
fromjcl job.jcl --to jcl          # byte-exact roundtrip
fromjcl job.jcl --to raw          # parse-tree dump
```

The parser is a pure-Python port of [Mike Fulton's
JCLParser](https://github.com/MikeFultonDev/JCLParser) (Apache 2.0).
Byte-exact roundtrip is enforced by the test corpus on every change.

## Install

```bash
pip install fromjcl
```

Python 3.12+. The runtime install is pure Python (PyYAML only) so it
works under IBM Open Enterprise Python on z/OS as well as
Linux/macOS/Windows.

## Quick start

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
```

## Python API

```python
from fromjcl import parse, Job

job = Job.from_parsed(parse("test.jcl"))
for step in job.steps:
    print(step.name, step.program, [dd.name for dd in step.dds])
```

## z/OS notes

JCL input files read via standard z/OS UNIX semantics. If you hit a
silent decode failure, check the file tag (`ls -T`) and convert to
ASCII (`iconv -f IBM-1047 -t ISO8859-1`) before running.

If `pip install` itself trips over EBCDIC tagging, set
`_BPXK_AUTOCVT=ON` in the install shell.

## Development

```bash
uv sync --all-groups
tests/check.sh        # ruff format + check, mypy, vulture, pytest
```

`test` group is z/OS-installable (pytest only). `dev` group adds
workstation-only tooling (ruff, mypy, vulture, radon, interrogate);
ruff and uv are Rust binaries with no z/OS build.

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): parser layout and IR

## Acknowledgments

The JCL scanner is a Python port of [Mike Fulton's
JCLParser](https://github.com/MikeFultonDev/JCLParser) (Apache 2.0).

## License

Apache-2.0. See [LICENSE](LICENSE).

## Trademarks

z/OS, IBM, MVS, and JCL are trademarks of International Business
Machines Corporation. This project is not affiliated with or endorsed
by IBM.
