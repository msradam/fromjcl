# json_samples

Generated from `tests/jcl_samples/` via `fromjcl <jcl> --to json`.
These exist to exercise the reverse path: `fromjcl --rejcl` reads
json back and emits JCL.

| sample                      | source jcl                                                  |
|-----------------------------|-------------------------------------------------------------|
| adrdssu_dump.json           | tests/jcl_samples/community/adrdssu_dump.jcl                |
| cond_compile_link_run.json  | tests/jcl_samples/community/cond_compile_link_run.jcl       |
| dfsort_merge.json           | tests/jcl_samples/community/dfsort_merge.jcl                |
| inlinedd.json               | tests/jcl_samples/parser_edge_cases/inlinedd.jcl            |
| proc.json                   | tests/jcl_samples/parser_edge_cases/proc.jcl                |

To refresh:

```sh
for s in adrdssu_dump cond_compile_link_run dfsort_merge; do
    uv run fromjcl tests/jcl_samples/community/$s.jcl --to json \
        -o tests/json_samples/$s.json
done
for s in inlinedd proc; do
    uv run fromjcl tests/jcl_samples/parser_edge_cases/$s.jcl --to json \
        -o tests/json_samples/$s.json
done
```
