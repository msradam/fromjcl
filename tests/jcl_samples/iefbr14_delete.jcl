//DELETEDS JOB (ACCT),'DELETE DATASET',CLASS=A,MSGCLASS=X,
//             NOTIFY=&SYSUID
//*************************************************************
//* DELETE AN EXISTING DATASET USING IEFBR14
//*************************************************************
//STEP01   EXEC PGM=IEFBR14
//DELFILE  DD DSN=USERID.OLD.DATASET,
//            DISP=(MOD,DELETE,DELETE),
//            UNIT=SYSDA
