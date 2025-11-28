//REPROJOB JOB (ACCT),'IDCAMS REPRO',CLASS=A,MSGCLASS=A,
//             NOTIFY=&SYSUID
//*************************************************************
//* COPY DATA BETWEEN DATASETS USING IDCAMS REPRO
//*************************************************************
//STEP01   EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//INPUT    DD DSN=USERID.INPUT.FILE,DISP=SHR
//OUTPUT   DD DSN=USERID.OUTPUT.FILE,DISP=SHR
//SYSIN    DD *
  REPRO INFILE(INPUT) OUTFILE(OUTPUT)
/*
