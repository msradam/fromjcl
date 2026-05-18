# Architecture

## Pipeline

```
JCL file -> parse() -> Job model -> serialize.* -> output
                              \
                               --> [zoau] -> classify_step -> shell renderer
```

1. **Parse** — `parser.py` calls the pure-Python scanner in `_scanner.py`,
   a port of Mike Fulton's [JCLParser](https://github.com/MikeFultonDev/JCLParser)
   scanner. Returns a complete scan tree with column metadata and raw
   record bytes for byte-exact roundtrip.
2. **Model** — `Job.from_parsed()` builds a typed dataclass tree
   (`Job` -> `Step` -> `DD` -> `Dataset`).
3. **Serialize** — `serialize/{json,yaml,csv,jcl,raw}.py` render either the
   model or the raw scan tree. `jcl.py` is byte-exact when given the raw
   tree; the rest are semantic.
4. **Classify (optional)** — under the `[zoau]` extra, `converters/classify.py`
   maps each step to a target-neutral `StepIntent` dataclass which the
   shell renderers consume.

## Module map

```
src/fromjcl/
├── _scanner.py               pure-Python JCL scanner, port of JCLParser
├── parser.py                 parse() / parse_bytes() entry points
├── models.py                 Job, Step, DD, Dataset, Disposition, Space, DCB
├── rejcl.py                  reverse path: text dump -> JCL
├── cli.py                    typer entry point (fromjcl.cli:main)
├── _validate.py              bashlex-based ZOAU shell validator ([zoau])
├── _zoau_flags.py            frozen ZOAU 1.x manpage flag table ([zoau])
├── serialize/                foundational outputs (no extras)
│   ├── raw.py                raw scan tree as JSON
│   ├── json.py               Job as cleaned JSON
│   ├── yaml.py               Job as cleaned block-style YAML
│   ├── csv.py                tabular CSV (one row per step/DD/dataset)
│   └── jcl.py                byte-exact JCL emitter
└── converters/               semantic translation, [zoau] only
    ├── classify.py           Step -> StepIntent (target-neutral)
    ├── common.py             shared helpers, mvscmd builder
    ├── _conditions.py        IF/COND -> shell `(( ))` expressions
    └── shell/
        ├── _scaffold.py      shared scaffold (header, conditionals, RC)
        ├── mvscmd.py         StepIntent -> mvscmd shell
        └── zoau.py           StepIntent -> ZOAU shell
```

## Classification (under `[zoau]`)

`classify.py` is the shared brain. Renderers dispatch by `isinstance(intent, ...)`.

| Intent | Source program | ZOAU output |
|---|---|---|
| `DatasetOps` | IEFBR14 create/delete | `dtouch` / `drm` |
| `CopyDataset` | IEBGENER, IEBCOPY | `dcp` / `decho` / `dcat` |
| `DeleteDatasets` | IDCAMS DELETE | `drm` / `mrm` (member) |
| `DefineGDG` | IDCAMS DEFINE GDG | `dtouch -tGDG` |
| `AlterRename` | IDCAMS ALTER NEWNAME | `dmv` |
| `ListCatalog` | IDCAMS LISTCAT | `dls` |
| `TSOCommands` | IKJEFT01 SYSTSIN | `tsocmd` |
| `ShellCommand` | BPXBATCH SH | passthrough |
| `PathRead` | IEBGENER PATH=... | `cat` |
| `BackupRestore` | ADRDSSU DUMP/RESTORE | `dzip` / `dunzip` |
| `IEHListOps` | IEHLIST LISTPDS / LISTVTOC | `mls` / `vtocls` |
| `IEHPROGMOps` | IEHPROGM RENAME / SCRATCH | `dmv` / `drm` |
| `TextReplace` | SORT FINDREP | `dsed` |
| `TextSearch` | ISRSUPC SRCHFOR | `dgrep` |
| `Fallback` | unrecognised program | `mvscmd` invocation |

Every emitted shell script carries an `EXPERIMENTAL` banner. The
`bashlex` validator runs on the output and flags any flag not in the
frozen ZOAU 1.x manpage table.

## Roundtrip guarantees

- **Byte-exact**: `serialize.jcl.convert(parse(x)) == x` for every
  sample in `tests/jcl_samples/`. The scan tree retains column metadata,
  comments, blank lines, and column 73-80 sequence numbers (where the
  source uses them).
- **Structural via JSON/YAML/CSV**: `Job.from_parsed(parse(rejcl(to_X(job)))) == Job.from_parsed(parse(x))`
  for every IBM, community, and ZOAU sample. The reverse path is lossy
  (column layout, comments, blank lines do not survive) but the Job
  IR is preserved exactly.

The 83-sample corpus exercises both guarantees on every commit; the
matrix lives in `tests/test_parser_roundtrip.py` (byte-exact) and
`tests/test_rejcl_matrix.py` (structural across 3 formats).

## Public API

The set re-exported from `fromjcl/__init__.py` is the stable surface.
Anything under `fromjcl._*` or `fromjcl.converters.*` is internal.

```python
from fromjcl import (
    parse, parse_bytes,
    Job, Step, DD, Dataset, Disposition, Space, DCB,
    to_json, to_yaml, to_csv, to_jcl, to_raw,
    from_dump,
)
```

`test_public_api.py` locks the surface in: adding or removing a name
fails the build.
