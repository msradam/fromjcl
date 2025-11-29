"""fromjcl/parser.py - JCL Parser - CFFI bindings to the C parser."""

from fromjcl._jclparser import ffi, lib


def parse(path: str) -> dict:
    """Parse a JCL file and return a structured dict."""
    opt = ffi.new("OptInfo_T*")
    prog = ffi.new("ProgInfo_T*")

    input_file = ffi.new("char[]", path.encode())
    opt.inputFile = input_file

    rc = lib.establishInput(opt, prog)
    if rc != 0:
        raise RuntimeError(f"Failed to open JCL file: {path} (error {rc})")

    rc = lib.scanJCL(opt, prog)
    if rc != 0:
        raise RuntimeError(f"Failed to parse JCL file: {path} (error {rc})")

    return _build_dict(prog.jcl)


def _build_dict(jcl) -> dict:
    """Walk the C parse tree and build a Python dict."""
    statements = []

    stmt = jcl.stmts.head
    while stmt != ffi.NULL:
        stmt_dict = {
            "type": ffi.string(stmt.type).decode() if stmt.type else None,
            "name": ffi.string(stmt.name).decode() if stmt.name else None,
            "parameters": [],
        }

        kvp = stmt.kvphead
        while kvp != ffi.NULL:
            key = ffi.string(kvp.key.txt).decode() if kvp.key.txt else None
            val = ffi.string(kvp.val.txt).decode() if kvp.val.txt else None
            stmt_dict["parameters"].append({"key": key, "value": val})
            kvp = kvp.next

        if stmt.conditional != ffi.NULL and stmt.conditional.text != ffi.NULL:
            stmt_dict["conditional"] = ffi.string(stmt.conditional.text).decode()

        if stmt.data != ffi.NULL and stmt.data.bytes != ffi.NULL and stmt.data.len > 0:
            stmt_dict["instream"] = ffi.string(stmt.data.bytes, stmt.data.len).decode()

        statements.append(stmt_dict)
        stmt = stmt.next

    return {"statements": statements}
