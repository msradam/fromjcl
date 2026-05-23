//KKELLEYD  JOB 'Y4004P,Y40,?','KEVIN KELLEY',                          
//             CLASS=B,MSGLEVEL=(1,1),NOTIFY=KKELLEY                    
//* ******************************************************************* 
//*            E.I. DUPONT                                            * 
//*                                          8 DAYS                   * 
//*            MVS/XA 2.1.7 8606 LEVEL                                * 
//*            JES3   2.1.5 8603 LEVEL                                * 
//*                                                                   * 
//*            SY2  3090-200  JES3 GLOBAL, CICS                       * 
//*            SY3  3090-200  BACK-UP, BATCH, TEST                    * 
//*            SY4  3090-200  TSO                                     * 
//*            SY8  3090-200  IMS                                     * 
//*                                                                   * 
//* ******************************************************************* 
/*JOBPARM LINES=200                                                     
/*SETUP    TAPE=PJ2355                                                  
/*SETUP    TAPE=ZOW21A                                                  
/*MESSAGE  TAPE 'PJ2355' IS NOT A MYERS CORNERS CARTRIDGE               
/*MESSAGE  TAPE 'ZOW21A' IS NOT A MYERS CORNERS CARTRIDGE               
//*                                                                     
//* ******************************************************************* 
//*            ALL MESSAGES.                                          * 
//* ******************************************************************* 
//STDOUT   OUTPUT CLASS=I,FORMS=STD,JESDS=ALL,                          
//             CHARS=GT20,FCB=STDC,COPIES=1                             
//MSGRATE   EXEC PGM=MSGLG212,REGION=5000K                              
//STEPLIB   DD DSN=KKELLEY.MSGLGPGM.LOAD,DISP=SHR                       
//OPTIN     DD *                                                        
TITLE: E.I. DUPONT   4-WAY 3090-200 JES3 COMPLEX                        
LOGTYPE(DLOG)                                                           
REPORT(ALL)                                                             
RATEMSGS(ALL)                                                           
//*-------------------------------------------------------------------* 
//*   'DUMPTBL(MSG,RATE)' SHOULD BE SPECIFIED AS AN OPTION IF         * 
//*   STATISTICAL DATA IS BEING COLLECTED FOR RETURN TO IBM.          * 
//*-------------------------------------------------------------------* 
//DATA     DD UNIT=3480,VOL=SER=PJ2355,LABEL=(1,SL),                    
//            DSN=XDCK.SYSLOG.HISTORY,                                  
//            DCB=(RECFM=FB,LRECL=133,BLKSIZE=13300),                   
//            DISP=OLD                                                  
//         DD UNIT=3480,VOL=SER=ZOW21A,LABEL=(1,SL),                    
//            DSN=XDCK.SYSLOG.HISTORY,                                  
//            DCB=(RECFM=FB,LRECL=133,BLKSIZE=13300),                   
//            DISP=OLD                                                  
//TTLLIB    DD DSN=KKELLEY.MSGLGTBL.TEXT,DISP=SHR                       
//SYSUDUMP  DD SYSOUT=(I,,WIDE),CHARS=DUMP                              
//SYSPRINT  DD SYSOUT=(,),OUTPUT=(*.STDOUT)                             
//*-------------------------------------------------------------------* 
//*  IF USED, THE FOLLOWING DD'S SHOULD HAVE:  OUTPUT=(*.STDOUT)      * 
//*-------------------------------------------------------------------* 
//PRNTOUT   DD SYSOUT=(,),OUTPUT=(*.STDOUT)                             
//COMPRATE  DD SYSOUT=(,),OUTPUT=(*.STDOUT)                             
//COMPMSG   DD SYSOUT=(,),OUTPUT=(*.STDOUT)                             
//UNKNOWN   DD DUMMY                                                    
//PREVIEW   DD SYSOUT=(,),OUTPUT=(*.STDOUT)                             
//IMSGRATE  DD DUMMY                                                    
//BURST     DD DUMMY                                                    
//*-------------------------------------------------------------------* 
//*  THE FOLLOWING DD'S ARE USED TO DUMP INTERNAL TABLES FOR REUSE.   * 
//*                                                                   * 
//*  ----> IF USED, 'DUMPRATE' -MUST- HAVE A DISP OF 'MOD' <----      * 
//*                                                                   * 
//*  THE 'DUMPMSG' DD AND 'DUMPRATE' DD SHOULD BE SPECIFIED IF        * 
//*  STATISTICAL DATA IS BEING COLLECTED FOR RETURN TO IBM.           * 
//*-------------------------------------------------------------------* 
//DUMPCNT   DD DUMMY                                                    
//DUMPMSG   DD DUMMY                                                    
//DUMPCMD   DD DUMMY                                                    
//DUMPRATE  DD DUMMY                                                    
//OUT       DD DUMMY                                                    
