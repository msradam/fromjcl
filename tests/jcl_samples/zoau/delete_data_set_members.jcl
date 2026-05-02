//*
//* Remove (delete) the PDS member MORTGAGE from
//* the dataset @@HLQ@@.ZOASAMP.PROJ23.COBOL
//* Returns 0 if successful, non-zero otherwise
//*
//MRM     EXEC PGM=IDCAMS
//SYSPRINT DD SYSOUT=*
//SYSIN DD *
  DELETE @@HLQ@@.ZOASAMP.PROJ23.COBOL(MORTGAGE)
/*
