# JCLParser samples

Verbatim from [github.com/MikeFultonDev/JCLParser](https://github.com/MikeFultonDev/JCLParser),
under `testsrc/`. Mike's `tests/regression.sh` enforces byte-exact roundtrip.

| File                  | Source                       | Notes |
| --------------------- | ---------------------------- | ----- |
| `command.jcl`         | `testsrc/command.jcl`        | COMMAND statement + freestanding `// SETPROG` |
| `comments.jcl`        | `testsrc/comments.jcl`       | Comment lines |
| `coupledd.jcl`        | `testsrc/coupledd.jcl`       | DD concatenation |
| `crthfs.jcl`          | `testsrc/crthfs.jcl`         | BPXBATCH / HFS create |
| `output.jcl`          | `testsrc/output.jcl`         | JES2 OUTPUT |
| `proc.jcl`            | `testsrc/proc.jcl`           | Inline PROC with params |
| `procnoparm.jcl`      | `testsrc/procnoparm.jcl`     | Inline PROC without params |
| `simplerinlinedd.jcl` | `testsrc/simplerinlinedd.jcl`| `DD *` instream |
| `cancel.jcl`          | `testsrc/cancel.skipjcl`     | JES CANCEL command |
| `inlinedd.jcl`        | `testsrc/inlinedd.skipjcl`   | Inline DD edge case |
| `splitsubparm.jcl`    | `testsrc/splitsubparm.skipjcl`| DCB subparm split across continuation |
| `subparm.jcl`         | `testsrc/subparm.skipjcl`    | Multi-line PARM with subparms |

The following files are hand-authored originals written for this project:

| File                      | Notes |
| ------------------------- | ----- |
| `lowercase_jobname.jcl`   | Jobname containing lowercase characters (template placeholder pattern); exercises the name-char validation fix in 0.4.0 |
| `acct_multi_element.jcl`  | JOB card with a parenthesised multi-element account field `(ACCT001,BIN1,BLDG2,DEPT3)`; exercises the paren-nesting fix in 0.4.0 |
