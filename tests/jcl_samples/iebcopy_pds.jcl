//COPYPDS  JOB (ACCT),'COPY PDS MEMBERS',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*************************************************************
//* COPY ALL MEMBERS FROM ONE PDS TO ANOTHER
//*************************************************************
//STEP01   EXEC PGM=IEBCOPY
//SYSPRINT DD SYSOUT=*
//INPDS    DD DSN=USERID.SOURCE.PDS,DISP=SHR
//OUTPDS   DD DSN=USERID.TARGET.PDS,DISP=SHR
//SYSIN    DD *
  COPY INDD=INPDS,OUTDD=OUTPDS
/*
