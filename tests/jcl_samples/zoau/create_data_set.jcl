//*
//* Allocate a partitioned dataset that is about 5M (89 tracks)
//*
//DTOUCH EXEC PGM=IEFBR14
//NEW    DD DSN=@@HLQ@@.DATA.PDS,DISP=(NEW,CATLG),                     +
//       DCB=(LRECL=133,RECFM=FBA),SPACE=(TRK,(89,89,20)),DSORG=PO
