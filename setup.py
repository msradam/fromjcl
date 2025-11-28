from setuptools import setup

setup(
    cffi_modules=["src/fromjcl/_build_parser.py:ffi"],
)