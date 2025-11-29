"""fromjcl/_build_parser.py - CFFI build script for JCL parser."""

from cffi import FFI
from pathlib import Path
import os

ffi = FFI()

ffi.cdef(
    """
    typedef struct {
        const char* arguments;
        const char* inputFile;
        ...;
    } OptInfo_T;
    
    typedef struct JCLStmt JCLStmt_T;
    typedef struct KeyValuePair KeyValuePair_T;
    
    typedef struct {
        size_t len;
        char* txt;
    } VarStr_T;
    
    typedef struct {
        char* text;
        ...;
    } ConditionalExpression_T;
    
    typedef struct {
        size_t len;
        char retainDelim[3];
        char* bytes;
    } InlineData_T;
    
    struct KeyValuePair {
        struct KeyValuePair* next;
        VarStr_T key;
        VarStr_T val;
        ...;
    };
    
    struct JCLStmt {
        struct JCLStmt* next;
        char* name;
        const char* type;
        size_t lines;
        void* scanhead;
        void* scantail;
        KeyValuePair_T* kvphead;
        void* kvptail;
        ConditionalExpression_T* conditional;
        InlineData_T* data;
        void* firstJCLLine;
    };
    
    typedef struct {
        JCLStmt_T* head;
        ...;
    } JCLStmts_T;
    
    typedef struct {
        void* infp;
        void* lines;
        JCLStmts_T* stmts;
    } JCL_T;
    
    typedef struct {
        JCL_T* jcl;
        void* gen;
    } ProgInfo_T;
    
    int establishInput(OptInfo_T* optInfo, ProgInfo_T* progInfo);
    int scanJCL(OptInfo_T* optInfo, ProgInfo_T* progInfo);
"""
)

ffi.set_source(
    "fromjcl._jclparser",
    '#include "scanjcl.h"',
    sources=["parser/src/scanjcl.c", "parser/src/jclmsgs.c"],
    include_dirs=["parser/src"],
)

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    ffi.compile(verbose=True)
