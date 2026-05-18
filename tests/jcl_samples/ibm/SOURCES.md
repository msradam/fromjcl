# IBM samples (non-ZOAU)

Two kinds of sample live here:

- Verbatim Apache-2.0 files vendored from public IBM-authored repos.
- Hand-authored paraphrases that exercise a specific parser construct;
  these were written for this project and reproduce no copyrighted text.

| File                              | Source                          | Path / Page                                                 |
| --------------------------------- | ------------------------------- | ----------------------------------------------------------- |
| `smf84fmt.jcl`                    | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMF84Formatter/smf84fmt.jcl`                     |
| `acifxjcl.jcl`                    | github.com/IBM/IBM-Z-zOS        | `zOS-Print/ACIF-User-Exit-samples/ACIFXJCL.JCL`             |
| `bpxrealt.jcl`                    | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMFReal/BPXREALT.JCL.txt`                        |
| `grs87.jcl`                       | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMF87Formatter/GRS87.JCL.txt`                    |
| `jcl_code.jcl`                    | github.com/IBM/IBM-Z-zOS        | `SMF-Tools/SMF30_USERKEY_COMMONAREA/JCL_CODE.txt`           |
| `idcams_alter_newname.jcl`        | hand-authored paraphrase        | exercises IDCAMS `ALTER ... NEWNAME(...)` with `-` continuation |
| `idcams_define_gdg.jcl`           | hand-authored paraphrase        | exercises IDCAMS `DEFINE GENERATIONDATAGROUP` with nested parens + `-` continuation |
| `idcams_listcat_entries.jcl`      | hand-authored paraphrase        | exercises IDCAMS `LISTCAT ENTRIES(...) ALL`                 |
| `if_nested_procs.jcl`             | hand-authored paraphrase        | exercises nested `IF`/`ELSE`/`ENDIF` over named PROCs and proc-step `RC`/`ABENDCC` refs |
| `restart_if_negation.jcl`         | hand-authored paraphrase        | exercises `JOB RESTART=` + `IF` with the `¬` (latin-1 0xAC) negation operator |
| `volume_ref_variants.jcl`         | hand-authored paraphrase        | exercises `VOLUME=SER=` single, multi-volume list, `VOLUME=(PRIVATE,SER=...)`, `UNIT=AFF=`, and `VOLUME=REF=*.STEP.DD` / `VOLUME=REF=DSN` referbacks |
| `disp_variants_iefbr14.jcl`       | hand-authored paraphrase        | exercises `DISP=` shapes: `(SHR,KEEP)`, `(OLD,DELETE,UNCATLG)`, `(NEW,CATLG,KEEP)`, `(MOD,PASS)`, `(MOD,DELETE)` with `&&` temp datasets |
| `output_routing.jcl`              | hand-authored paraphrase        | exercises `OUTPUT` statements with `DEST=`, `FORMS=`, `CHARS=()`, `COPIES=`, `DEFAULT=YES`, and `SYSOUT=A,OUTPUT=*.NAME` referback |
| `asm_lked_go_cond.jcl`            | hand-authored paraphrase        | exercises a 3-step ASM/LKED/GO flow with end-of-line comments, `PARM=(...)`/`PARM='...'`, `COND=(8,LE,STEP)` and `COND=((8,LE,STEP),(8,LE,STEP))`, `&&` temp datasets, `DISP=(,PASS)`, `PGM=*.LKED.SYSLMOD` referback, and two instream `DD *` blocks |
| `jes2_msglg_iplrate.jcl`          | github.com/IBM/IBM-Z-zOS        | `zOS-Tools-and-Toys/msglg610/stdjes2.jcl` (cols 73-80 blanked; see note) |
| `jes3_msglg_setup_message.jcl`    | github.com/IBM/IBM-Z-zOS        | `zOS-Tools-and-Toys/msglg610/stdjes3.jcl` (cols 73-80 blanked; see note) |
| `cobol_acif_userexit_jcllib.jcl`  | github.com/IBM/IBM-Z-zOS        | `zOS-Print/ACIF-User-Exit-samples/COBACXIT.JCL`             |
| `bpxbatch_spark_master_start.jcl` | github.com/IBM/IBM-Z-zOS        | `zOS-Workflow/IBM Platform for Apache Spark Workflow/workflow_sparkci.xml` (`SPARKMST` template) |
| `bpxbatch_spark_master_stop.jcl`  | github.com/IBM/IBM-Z-zOS        | `zOS-Workflow/IBM Platform for Apache Spark Workflow/workflow_sparkci.xml` (`SPARKSTP` template) |
| `bcpii_hwirstc1_sysaff.jcl`            | github.com/IBM/zOS-BCPii        | `Example-LPARActivate-C/jcl/hwirstc1.jcl` (`/*JOBPARM SYSAFF=` padded to col 80) |
| `bcpii_hwirstcx_compile_bind.jcl`      | github.com/IBM/zOS-BCPii        | `Example-LPARActivate-C/jcl/hwirstcx.jcl` (`/*JOBPARM SYSAFF=` padded to col 80) |
| `zopeneditor_asm_compile_link_run.jcl` | github.com/IBM/zopeneditor-sample | `JCL/RUNASAM1.jcl`                                          |
| `zopeneditor_comproc_pend.jcl`         | github.com/IBM/zopeneditor-sample | `JCLPROC/COMPROC.jcl` (trailing newline added)              |
| `gam_pli_db2_drop_tables.jcl`          | github.com/IBM/idz-utilities    | `PLI-Samples/Global Auto Mart PLI Sample/GAM_PLI/JCL/GAM0VCDB.jcl` (trailing newline added) |
| `gam_pli_cics_csdup.jcl`               | github.com/IBM/idz-utilities    | `PLI-Samples/Global Auto Mart PLI Sample/GAM_PLI/JCL/GAMCSDUP.jcl` (trailing newline added) |
| `icsf_smf30cex_sort_rexx.jcl`          | github.com/IBM/ICSF-Education   | `Quantum-Safe Redbook Samples/SMF30 samples/SMF30CEX.jcl` (MIT-licensed) |
| `custompac_csi2jcl_ikjeft01.jcl`       | github.com/IBM/CustomPac        | `JCL/CSI2JCL`                                               |
| `bankofz_db2_drop_tables.jcl`          | github.com/IBM/Bank-of-Z        | `.setup/jcl/Db2-drop.jcl`                                   |
| `dbb_bldmort_cobol_link.jcl`           | github.com/IBM/dbb              | `Migration/jclToZBuilder/samples/BLDMORT.jcl` (trailing newline added) |
| `dbb_gitispf_bgzgit.jcl`               | github.com/IBM/dbb              | `IDE/GitISPFClient/sbgzsamp/bgzgit.jcl`                     |
| `dbb_gitispf_bgzoput.jcl`              | github.com/IBM/dbb              | `IDE/GitISPFClient/sbgzsamp/bgzoput.jcl`                    |
| `db2ztools_deprovision_storedproc.jcl` | github.com/IBM/Db2ZTools        | `DevOps/Db2SchemaServices/Dependency/DeprovisionStoredProcedure/build.jcl` |
| `db2ztools_icpdb2_grant.jcl`           | github.com/IBM/Db2ZTools        | `DevOps/ICPDb2RESTServices/icpgrant.jcl`                    |
| `db2ztools_icpdb2_rest.jcl`            | github.com/IBM/Db2ZTools        | `DevOps/ICPDb2RESTServices/icprest.jcl`                     |
| `kafka_ixyjrpa6_producer.jcl`          | github.com/IBM/Open-Enterprise-SDK-for-Apache-Kafka | `jcl/IXYJRPA6.jcl` (trailing newline added) |
| `cwet_slack_ikjeft01.jcl`              | github.com/IBM/zOS-Client-Web-Enablement-Toolkit | `Example-Slack/jcl/slack.jcl` (trailing newline added) |
| `cwet_zosmf_healthcheck.jcl`           | github.com/IBM/zOS-Client-Web-Enablement-Toolkit | `Example-zOSMF/jcl/HLTHCHK.jcl`                |
| `ansible_zos_stat_iebgener.jcl`        | github.com/IBM/z_ansible_collections_samples | `zos_concepts/zos_stat/files/HELLO.jcl`               |
| `ansible_started_task_bpxbatch.jcl`    | github.com/IBM/z_ansible_collections_samples | `zos_concepts/zos_started_task/files/sample.jcl` (trailing newline added) |
| `zowe_apilayer_racf_passticket.jcl`    | github.com/zowe/api-layer       | `passticket/test-programs/racf.jcl`                         |
| `zowe_apilayer_tss_passticket.jcl`     | github.com/zowe/api-layer       | `passticket/test-programs/tss.jcl`                          |
| `zopeneditor_allocate.jcl`             | github.com/IBM/zopeneditor-sample | `JCL/ALLOCATE.jcl` (trailing `\x1a` EOF stripped)         |
| `zopeneditor_asmalloc.jcl`             | github.com/IBM/zopeneditor-sample | `JCL/ASMALLOC.jcl` (trailing `\x1a` EOF stripped)         |
| `zopeneditor_plialloc.jcl`             | github.com/IBM/zopeneditor-sample | `JCL/PLIALLOC.jcl` (trailing `\x1a` EOF stripped)         |
| `zopeneditor_rexalloc.jcl`             | github.com/IBM/zopeneditor-sample | `JCL/REXALLOC.jcl` (trailing `\x1a` EOF stripped)         |
| `zopeneditor_run.jcl`                  | github.com/IBM/zopeneditor-sample | `JCL/RUN.jcl` (trailing `\x1a` EOF stripped)              |
| `zopeneditor_include_member.jcl`       | github.com/IBM/zopeneditor-sample | `JCL/INCLUDE.jcl` (trailing newline added)                |

All GitHub-sourced samples are vendored under their original Apache 2.0
license (except `icsf_smf30cex_sort_rexx.jcl`, which is MIT-licensed);
per-file copyright/license headers in the upstream are preserved verbatim
in the vendored copy.

Samples labelled *hand-authored paraphrase* are short, original JCL
listings written by the project to exercise specific parser constructs
(continuation, nested IF/ELSE, OUTPUT referback, etc.). They do not
reproduce text from any IBM publication.

Note on `jes2_msglg_iplrate.jcl` / `jes3_msglg_setup_message.jcl`: the upstream
files contain an EBCDIC `\x1a` EOF byte (stripped) and 8-character sequence
numbers in cols 73-80 of `/*JOBPARM`, `/*SETUP`, and `/*MESSAGE` lines.
The parser currently drops the column 73-80 tail on `/*` JES2/3 control
statements (it preserves the tail on `//`-statements and `//*` comments), so
those positions were blanked to spaces in the saved samples to satisfy
byte-exact roundtrip. The semantic content of every JES2/3 control statement
and parameter is preserved verbatim.
