//*
//* Delete the dataset @@HLQ@@.ZOASAMP.NOT.WANTED
//* Returns 0 if the dataset was successfully deleted
//* (or if it didn't exist).
//*
//DRM   EXEC PGM=IEFBR14
//DELDD DD DSN=@@HLQ@@.ZOASAMP.NOT.WANTED,                             +
//      DISP=(MOD,DELETE,DELETE),SPACE=(TRK,1)
