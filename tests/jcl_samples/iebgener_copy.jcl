//COPYFILE JOB (ACCT),'COPY DATASET',CLASS=A,MSGCLASS=A,
//             NOTIFY=&SYSUID
//*************************************************************
//* COPY A SEQUENTIAL DATASET USING IEBGENER
//*************************************************************
//STEP01   EXEC PGM=IEBGENER
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSUT1   DD DSN=USERID.SOURCE.DATA,DISP=SHR
//SYSUT2   DD DSN=USERID.TARGET.DATA,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(CYL,5,2),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=8000)
