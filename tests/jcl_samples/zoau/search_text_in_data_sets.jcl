//*
//* Search the dataset member @@HLQ@@.ZOASAMP.MY.GREP(FILETWO)
//* for the (case insensitive) string 'line'
//* printing results to OUTDD
//*
//DGREP EXEC PGM=ISRSUPC,                                             +
//      PARM='SRCHCMP,IDPRFX,NOSUMS,LONGLN,NOPRTCC'
//SYSIN DD *
  SRCHFOR 'line'
/*
//SYSPRINT DD SYSOUT=*
//NEWDD  DD DSN=@@HLQ@@.ZOASAMP.MY.GREP(FILETWO),DISP=SHR
//OUTDD  DD SYSOUT=*
