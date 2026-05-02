//*
//* Compare the PDSE members FILEONE and FILETWO from
//* the PDSE @@HLQ@@.ZOASAMP.MY.DIFF.
//* and write the results to OUTDD.
//* Return code from step is 0 if they are the same,
//* non-zero if different
//*
//DDIFF EXEC PGM=ISRSUPC,                                             +
//      PARM='LINECMP,LOCS,LONGLN,NOPRTCC,NOSUMS,DELTAL'
//SYSIN DD DUMMY
//SYSPRINT DD SYSOUT=*
//OLDDD  DD DSN=@@HLQ@@.ZOASAMP.MY.DIFF(FILEONE),DISP=SHR
//NEWDD  DD DSN=@@HLQ@@.ZOASAMP.MY.DIFF(FILETWO),DISP=SHR
//OUTDD  DD SYSOUT=*
