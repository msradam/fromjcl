//DEDUPJOB JOB (ACCT),'SORT AND DEDUP',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*************************************************************
//* SORT AND REMOVE DUPLICATE RECORDS
//*************************************************************
//STEP01   EXEC PGM=SORT
//SYSOUT   DD SYSOUT=*
//SORTIN   DD DSN=USERID.INPUT.DUPS,DISP=SHR
//SORTOUT  DD DSN=USERID.OUTPUT.UNIQUE,DISP=SHR
//SYSIN    DD *
  SORT FIELDS=(1,15,CH,A)
  SUM FIELDS=NONE
/*
