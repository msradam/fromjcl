# Architecture

## Pipeline

```
JCL file -> parse() -> Job model -> classify_step() -> renderer -> output
```

1. **Parse**: `parser.py` calls the pure-Python scanner in `_scanner.py`,
   which is a port of Mike Fulton's JCLParser scanner. Returns a complete
   scan tree with column metadata and raw record bytes for byte-exact
   roundtrip.
2. **Model**: `Job.from_parsed()` builds a typed dataclass tree
   (`Job` -> `Step` -> `DD` -> `Dataset`).
3. **Classify**: `classify_step()` reads a step's program, DDs, and
   SYSIN, returns a target-neutral `StepIntent` dataclass.
4. **Render**: each converter dispatches by `isinstance(intent, ...)`
   and emits target-specific output.

## Module map

```
src/fromjcl/
├── _scanner.py               pure-Python JCL scanner (port of MikeFultonDev/JCLParser)
├── parser.py                 parse(path) entry point
├── models.py                 Job, Step, DD, Dataset, Disposition, Space, DCB
├── _validate.py              bashlex + ibm_zos_core argspec validators
├── _zoau_flags.py            frozen table of ZOAU command flags
├── _ansible_modules.py       frozen table of ibm_zos_core argspecs
├── cli.py                    argparse entry point
├── serialize/                foundational outputs (no extras, no classifier)
│   ├── raw.py                raw scan tree as JSON
│   ├── json.py               Job as cleaned JSON
│   ├── yaml.py               Job as cleaned block-style YAML
│   ├── csv.py                tabular CSV view
│   └── jcl.py                byte-exact JCL roundtrip emitter
└── converters/               semantic translation (uses classify_step)
    ├── classify.py           Step -> StepIntent (target-neutral)
    ├── common.py             shared helpers, mvscmd / zos_mvs_raw fallbacks
    ├── _conditions.py        IF/COND -> shell (( )) and Ansible when:
    ├── _deps.py              step-level dependency graph (PASS, RC, dataset r/w)
    ├── zosmf.py              z/OSMF REST calls as Postman Collection v2.1
    ├── makefile.py           Makefile with parallel-eligible step DAG
    ├── shell/
    │   ├── _scaffold.py      shared shell scaffold (header, conditionals, RC capture)
    │   ├── mvscmd.py         StepIntent -> mvscmd shell
    │   └── zoau.py           StepIntent -> ZOAU shell
    └── ansible/
        ├── zos_core.py       StepIntent -> ibm_zos_core Ansible tasks
        └── zos_mvs_raw.py    Step -> zos_mvs_raw Ansible tasks (no classification)
```

## Classification

`classify.py` is the shared brain. Renderers are thin dispatchers over its output.

| Intent | Meaning | ZOAU | Ansible |
|---|---|---|---|
| `DatasetOps` | IEFBR14 create/delete | `dtouch` / `drm` | `zos_data_set` |
| `CopyDataset` | IEBGENER/IEBCOPY | `dcp` / `decho` | `zos_copy` |
| `DeleteDatasets` | IDCAMS DELETE | `drm` | `zos_data_set` absent |
| `DefineGDG` | IDCAMS DEFINE GDG | `dtouch -tGDG` | (none) |
| `AlterRename` | IDCAMS ALTER NEWNAME | `dmv` | (none) |
| `ListCatalog` | IDCAMS LISTCAT | `dls` | `zos_stat` (ENTRIES) / `zos_find` (LVL) |
| `TSOCommands` | IKJEFT01 | `tsocmd` | `zos_tso_command` |
| `ShellCommand` | BPXBATCH SH | passthrough | `zos_script` |
| `PathRead` | IEBGENER PATH=...,SYSUT2=SYSOUT | `cat` | `slurp` |
| `BackupRestore` | ADRDSSU DUMP/RESTORE | `dzip` / `dunzip` | `zos_backup_restore` |
| `IEHListOps` | IEHLIST LISTPDS | `mls` | `zos_find` |
| `IEHPROGMOps` | IEHPROGM RENAME/SCRATCH | `dmv` / `drm` | `zos_data_set` (SCRATCH only) |
| `TextReplace` | SORT FINDREP | `dsed` | (none) |
| `TextSearch` | ISRSUPC SRCHFOR | `dgrep` | (none) |
| `Fallback` | unrecognized program | `mvscmd` | `zos_mvs_raw` |

## Dependency analysis

`_deps.py` computes a precedence DAG from three signals:

- PASS pairs: a step that consumes `DISP=(...,PASS)` depends on the
  allocator.
- RC references: a step whose COND= or IF-condition mentions another
  step's `.RC` / `.ABEND` / `.RUN` / `.ABENDCC` depends on that step.
- Dataset read-after-write: a step that reads (`OLD`/`SHR`/`MOD`) or
  rewrites (`MOD`/`NEW`) a DSN depends on the most recent prior step
  that wrote (`NEW`/`MOD`) the same DSN.

Two converters consume the DAG:

- `zosmf.py` uses connected components to decide which steps must
  travel together in one JCL chunk versus which can fly as standalone
  REST calls.
- `makefile.py` uses direct predecessors as `make` deps so `make -j N`
  parallelises independent branches.

## Roundtrip guarantee

`parse()` retains column metadata and raw record bytes so
`serialize.jcl.convert(parse(x)) == x` byte-for-byte. The 50-sample
corpus in `tests/jcl_samples/` exercises this on every commit.

## Public API

```python
from fromjcl import parse, Job

job = Job.from_parsed(parse("job.jcl"))
```
