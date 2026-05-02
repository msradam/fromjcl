//*
//* Rename the PDSE member PAYMENT to PAYMENTS in
//* PDSE @@HLQ@@.ZOASAMP.PROJ23.COBOL.
//* Note the volume that the PDSE resides on must be
//* specified in place of @@VOL@@
//*
//MMV     EXEC PGM=IEHPROGM
//SYSPRINT DD SYSOUT=*
//DD       DD DSN=@@HLQ@@.ZOASAMP.PROJ23.COBOL,                        +
//         UNIT=SYSALLDA,DISP=OLD,VOL=SER=@@VOL@@
//SYSIN DD *
 RENAME VOL=SYSALLDA=@@VOL@@,                                           +
               DSNAME=@@HLQ@@.ZOASAMP.PROJ23.COBOL,                    +
               NEWNAME=PAYMENTS,MEMBER=PAYMENT
/*
