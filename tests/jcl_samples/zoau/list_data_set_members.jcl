//*
//* List the members of the dataset @@HLQ@@.ZOASAMP.PROJ23.COBOL
//* to SYSPRINT (console). Note that the volume that the dataset
//* resides on must also be provided instead of @@VOL@@.
//* Returns 0 if successful, non-zero otherwise
//*
//MLS      EXEC PGM=IEHLIST
//SYSPRINT DD SYSOUT=*
//DD       DD DSN=@@HLQ@@.ZOASAMP.PROJ23.COBOL,                        +
//         UNIT=SYSALLDA,DISP=OLD,VOL=SER=@@VOL@@
//SYSIN    DD *
  LISTPDS DSNAME=@@HLQ@@.ZOASAMP.PROJ23.COBOL,VOL=SYSALLDA=@@VOL@@
/*
