//CREATEPS JOB (ACCT),'CREATE PS FILE',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*************************************************************
//* CREATE A NEW SEQUENTIAL (PS) DATASET USING IEFBR14
//*************************************************************
//STEP01   EXEC PGM=IEFBR14
//SYSPRINT DD SYSOUT=*
//NEWFILE  DD DSN=USERID.TEST.SEQFILE,
//            DISP=(NEW,CATLG,DELETE),
//            SPACE=(TRK,10,5),
//            UNIT=SYSDA,
//            DCB=(DSORG=PS,RECFM=FB,LRECL=80,BLKSIZE=8000)
