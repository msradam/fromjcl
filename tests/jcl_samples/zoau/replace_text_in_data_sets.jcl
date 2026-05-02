//*
//* Search for the string 'Lines' in the dataset
//* @@HLQ@@ZOASAMP.MY.DSED and replace each occurrence
//* with 'Records'.
//* Write the output to the same dataset as was used for
//* input.
//* Returns 0 if successful, non-zero if an error occurred.
//*
//DSED EXEC PGM=SORT,                                                 +
//      PARM='NOLIST'
//SYSIN DD *
 SORT FIELDS=COPY
 INREC FINDREP=(IN=C'Lines',
 OUT=C'Records')
/*
//SYSOUT  DD SYSOUT=*
//SORTIN  DD DSN=@@HLQ@@.ZOASAMP.MY.DSED,DISP=SHR
//SORTOUT DD DSN=@@HLQ@@.ZOASAMP.MY.DSED,DISP=SHR
