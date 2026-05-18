---
marp: true
theme: neobrutalism
paginate: false
size: 16:9
style: |
  section {
    --nb-accent: #f5c842;
    padding: 36px 48px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .hdr {
    display: flex;
    align-items: baseline;
    gap: 18px;
    margin-bottom: 18px;
  }
  h1 {
    margin: 0;
    font-size: 56px;
    line-height: 1;
  }
  .tag {
    background: var(--nb-accent);
    border: 2px solid var(--nb-border);
    box-shadow: var(--nb-shadow);
    padding: 6px 14px;
    font-size: 18px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .sub {
    font-size: 20px;
    margin: 0 0 28px 0;
    color: var(--nb-text-secondary);
  }
  .row {
    display: grid;
    grid-template-columns: 1fr 70px 1fr;
    gap: 28px;
    align-items: stretch;
  }
  .col h3 {
    font-size: 18px;
    margin: 0 0 10px 0;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .col pre {
    margin: 0 0 16px 0;
    font-size: 15px;
    line-height: 1.4;
  }
  .col pre:last-child {
    margin-bottom: 0;
  }
  .arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 8px;
  }
  .arrow .a {
    font-size: 64px;
    font-weight: 900;
    line-height: 1;
  }
  .arrow .c {
    font-family: var(--nb-mono);
    font-size: 12px;
    background: var(--nb-accent);
    border: 2px solid var(--nb-border);
    padding: 3px 8px;
    white-space: nowrap;
  }
---

<div class="hdr">
<h1>fromjcl</h1>
<span class="tag">Apache 2.0 • Python 3.12+</span>
</div>

<p class="sub">Parse IBM z/OS JCL. Emit JSON, YAML, CSV, ZOAU shell, or byte-exact JCL.</p>

<div class="row">
<div class="col">

### JCL in

```jcl
//ALLOCJ   JOB  1234,'DEMO'
//STEP1    EXEC PGM=IEFBR14
//NEW      DD   DSN=USR.WORK.DEMO.PDS,
//              DISP=(NEW,CATLG),
//              SPACE=(TRK,(10,5,5)),
//              DCB=(RECFM=FB,LRECL=80,
//                   DSORG=PO)
```

</div>
<div class="arrow">
<span class="a">→</span>
<span class="c">fromjcl</span>
</div>
<div class="col">

### YAML out

```yaml
name: ALLOCJ
steps:
- name: STEP1
  program: IEFBR14
  dds:
  - name: NEW
    datasets:
    - dsn: USR.WORK.DEMO.PDS
```

### ZOAU shell out

```sh
dtouch -tpdse -l80 -rFB -s10T \
  "USR.WORK.DEMO.PDS"
```

</div>
</div>
