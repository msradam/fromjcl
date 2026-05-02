//*
//* Write text from SYSUT1 (inline text)
//* to the dataset member **HLQ**.ZOASAMP.SAMPLE.TEXT(MEMBER#1)
//*
//DECHO    EXEC PGM=IEBGENER
//SYSPRINT DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSUT1   DD *
This text will be
written to the PDSE member MEMBER#1
as 3 records
/*
//SYSUT2   DD DSN=@@HLQ@@.ZOASAMP.SAMPLE.TEXT(MEMBER#1),DISP=SHR
