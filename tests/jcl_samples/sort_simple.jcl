//SORTJOB  JOB (ACCT),'SIMPLE SORT',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*************************************************************
//* SORT A FILE BY KEY FIELD
//*************************************************************
//STEP01   EXEC PGM=SORT
//SYSOUT   DD SYSOUT=*
//SORTIN   DD DSN=USERID.UNSORTED.DATA,DISP=SHR
//SORTOUT  DD DSN=USERID.SORTED.DATA,DISP=SHR
//SYSIN    DD *
  SORT FIELDS=(1,10,CH,A)
/*
