# fromjcl

Convert JCL to modern formats.

```bash
fromjcl job.jcl --to mvscmd     # Shell script for z/OS USS
fromjcl job.jcl --to ansible    # Ansible playbook
fromjcl job.jcl --to json       # Structured JSON
fromjcl job.jcl --to yaml       # Structured YAML
```

## Installation

```bash
pip install fromjcl
```

## Quick Start

**Input** (`test.jcl`):
```jcl
//TESTJOB  JOB (ACCT),'TEST',CLASS=A,MSGCLASS=X
//STEP01   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
 /* HELLO FROM FROMJCL */
/*
```

**Parse to YAML** (`fromjcl test.jcl --to yaml`):
```yaml
name: TESTJOB
account: (ACCT)
programmer: TEST
class_: A
msgclass: X
steps:
- name: STEP01
  program: IDCAMS
  dds:
  - name: SYSPRINT
    sysout: '*'
  - name: SYSIN
    instream: " /* HELLO FROM FROMJCL */"
```

**Generate and run on z/OS** (`fromjcl test.jcl --to mvscmd | sed 's/mvscmd/mvscmdauth/' | sh`):
```
1IDCAMS  SYSTEM SERVICES                                           TIME: 12:00:00        01/01/25     PAGE      1
0        
  /* HELLO FROM FROMJCL */
0IDC0002I IDCAMS PROCESSING COMPLETE. MAXIMUM CONDITION CODE WAS 0
```

## Python API

```python
from fromjcl import parse, Job

job = Job.from_parsed(parse("test.jcl"))

print(f"Job '{job.name}' has {len(job.steps)} step(s):")
for step in job.steps:
    dd_names = [dd.name for dd in step.dds]
    print(f"  {step.name} runs {step.program} with DDs: {', '.join(dd_names)}")
```

```
Job 'TESTJOB' has 1 step(s):
  STEP01 runs IDCAMS with DDs: SYSPRINT, SYSIN
```

## Roadmap

Currently working on:

- **Authorized programs** - Auto-detecting when to use `mvscmdauth` vs `mvscmd`
- **Multiple instream DDs** - Handling steps with more than one `DD *`
- **PROC expansion** - Expanding procedure calls inline

## Acknowledgments

JCL parsing uses [Mike Fulton's JCLParser](https://github.com/MikeFultonDev/JCLParser), licensed under Apache 2.0.

## License

MIT