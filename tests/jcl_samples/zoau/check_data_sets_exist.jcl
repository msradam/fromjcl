//*
//* Check if dataset @@HLQ@@.ZOASAMP.MY.JCL exists
//* If it does, return code from step will be 0.
//* Otherwise it will be non-zero.
//*
//DSEXIST EXEC PGM=IDCAMS
//SYSPRINT DD DUMMY
//SYSIN DD *
  LISTCAT ENTRIES('@@HLQ@@.ZOASAMP.MY.JCL')
/*
