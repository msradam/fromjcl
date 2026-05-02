//*
//* List all the datasets that start with
//* to @@HLQ.ZOASAMP
//*
//DLS      EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//AMSDUMP  DD DUMMY
//SYSIN    DD *
  LISTCAT LVL(@@HLQ@@.ZOASAMP) ALL
/*
