# IBM samples (non-ZOAU)

Verbatim from public IBM-authored sources outside the ZOAU example pages.

| File                              | Source                          | Path / Page                                                 |
| --------------------------------- | ------------------------------- | ----------------------------------------------------------- |
| `smf84fmt.jcl`                    | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMF84Formatter/smf84fmt.jcl`                     |
| `acifxjcl.jcl`                    | github.com/IBM/IBM-Z-zOS        | `zOS-Print/ACIF-User-Exit-samples/ACIFXJCL.JCL`             |
| `bpxrealt.jcl`                    | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMFReal/BPXREALT.JCL.txt`                        |
| `grs87.jcl`                       | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMF87Formatter/GRS87.JCL.txt`                    |
| `jcl_code.jcl`                    | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMF30_USERKEY_COMMONAREA/JCL_CODE.txt`           |
| `dfsms_ams_alter_newname.jcl`     | DFSMS Access Method Services    | SC23-6846-40 (V2R4), p.107 — `ALTER ... NEWNAME(...)`       |
| `dfsms_ams_define_gdg.jcl`        | DFSMS Access Method Services    | SC23-6846-40 (V2R4), p.215 — `DEFINE GENERATIONDATAGROUP`   |
| `dfsms_ams_listcat_entries.jcl`   | DFSMS Access Method Services    | SC23-6846-40 (V2R4), p.319 — `LISTCAT ENTRIES(...) ALL`     |
| `jcl_ref_if_nested.jcl`           | MVS JCL Reference               | SA23-1385-40 (V2R4), p.421 — nested IF/ELSE                 |
| `jcl_ref_restart_if.jcl`          | MVS JCL Reference               | SA23-1385-40 (V2R4), p.422 — `RESTART=` + IF                |
| `jcl_ug_volume_ref.jcl`           | MVS JCL User's Guide            | SA23-1386-40 (V2R4), p.143 — VOLUME / AFF / REF             |
| `jcl_ug_disp_variants.jcl`        | MVS JCL User's Guide            | SA23-1386-40 (V2R4), p.196 — IEFBR14 DISP combinations      |
| `jcl_ug_output_routing.jcl`       | MVS JCL User's Guide            | SA23-1386-40 (V2R4), p.213 — OUTPUT statements              |
| `jcl_ug_asm_lked_go.jcl`          | MVS JCL User's Guide            | SA23-1386-40 (V2R4), p.245 — ASM/LKED/GO with COND=         |
| `jes2_msglg_iplrate.jcl`          | github.com/IBM/IBM-Z-zOS        | `zOS-Tools-and-Toys/msglg610/stdjes2.jcl` (cols 73-80 blanked; see note) |
| `jes3_msglg_setup_message.jcl`    | github.com/IBM/IBM-Z-zOS        | `zOS-Tools-and-Toys/msglg610/stdjes3.jcl` (cols 73-80 blanked; see note) |
| `cobol_acif_userexit_jcllib.jcl`  | github.com/IBM/IBM-Z-zOS        | `zOS-Print/ACIF-User-Exit-samples/COBACXIT.JCL`             |
| `bpxbatch_spark_master_start.jcl` | github.com/IBM/IBM-Z-zOS        | `zOS-Workflow/IBM Platform for Apache Spark Workflow/workflow_sparkci.xml` (`SPARKMST` template) |
| `bpxbatch_spark_master_stop.jcl`  | github.com/IBM/IBM-Z-zOS        | `zOS-Workflow/IBM Platform for Apache Spark Workflow/workflow_sparkci.xml` (`SPARKSTP` template) |

GitHub samples are Apache 2.0; manual examples are reproduced for testing fair use.

Note on `jes2_msglg_iplrate.jcl` / `jes3_msglg_setup_message.jcl`: the upstream
files contain an EBCDIC `\x1a` EOF byte (stripped) and 8-character sequence
numbers in cols 73-80 of `/*JOBPARM`, `/*SETUP`, and `/*MESSAGE` lines.
The parser currently drops the column 73-80 tail on `/*` JES2/3 control
statements (it preserves the tail on `//`-statements and `//*` comments), so
those positions were blanked to spaces in the saved samples to satisfy
byte-exact roundtrip. The semantic content of every JES2/3 control statement
and parameter is preserved verbatim.
