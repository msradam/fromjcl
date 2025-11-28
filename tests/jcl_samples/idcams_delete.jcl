//DELJOB   JOB (ACCT),'DELETE VSAM',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*************************************************************
//* DELETE A VSAM CLUSTER USING IDCAMS
//*************************************************************
//STEP01   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN    DD *
  DELETE USERID.VSAM.KSDS CLUSTER PURGE
  SET MAXCC=0
/*
