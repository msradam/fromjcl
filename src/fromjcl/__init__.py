"""fromjcl - Convert JCL to modern formats."""

from fromjcl.parser import parse
from fromjcl.models import Job

__all__ = ["parse", "Job"]
