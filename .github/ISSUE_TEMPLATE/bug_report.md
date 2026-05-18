---
name: Bug report
about: Something fromjcl does that it shouldn't, or doesn't do that it should
labels: bug
---

### What happened

(A short summary. If the CLI exited with an error, paste the message.)

### Minimal JCL to reproduce

```jcl
//YOUR JOB
//STEP1 EXEC PGM=...
...
```

### What you ran

```
fromjcl yourfile.jcl --to ...
```

### What you expected

(Either the JCL feature that should have parsed, or the output shape
you expected.)

### Environment

- fromjcl version: `pip show fromjcl | grep Version`
- Python version: `python --version`
- OS: macOS / Linux / Windows / z/OS
- `[zoau]` extra installed? yes / no

### Anything else

(Stack trace, links to relevant IBM JCL Reference pages, etc.)
