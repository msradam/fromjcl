# yml_samples

Generated from `tests/jcl_samples/` via `fromjcl <jcl> --to yaml`.
These exist to exercise the reverse path: `fromjcl --rejcl` reads
yaml back and emits JCL.

| sample                     | source jcl                                                  |
|----------------------------|-------------------------------------------------------------|
| adrdssu_dump.yml           | tests/jcl_samples/community/adrdssu_dump.jcl                |
| cond_compile_link_run.yml  | tests/jcl_samples/community/cond_compile_link_run.jcl       |
| dfsort_merge.yml           | tests/jcl_samples/community/dfsort_merge.jcl                |
| inlinedd.yml               | tests/jcl_samples/parser_edge_cases/inlinedd.jcl            |
| proc.yml                   | tests/jcl_samples/parser_edge_cases/proc.jcl                |

To refresh:

```sh
for s in adrdssu_dump cond_compile_link_run dfsort_merge; do
    uv run fromjcl tests/jcl_samples/community/$s.jcl --to yaml \
        -o tests/yml_samples/$s.yml
done
for s in inlinedd proc; do
    uv run fromjcl tests/jcl_samples/parser_edge_cases/$s.jcl --to yaml \
        -o tests/yml_samples/$s.yml
done
```
