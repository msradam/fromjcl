"""fromjcl/__init__.py - Convert JCL to modern formats."""

from fromjcl.models import Job
from fromjcl.parser import parse

__all__ = ["parse", "Job"]
