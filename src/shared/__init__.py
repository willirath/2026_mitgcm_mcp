"""Shared physics utilities used by both MITgcm and FESOM2 MCP servers."""

from .translate import translate_lab_params
from .scales import check_scales

__all__ = ["translate_lab_params", "check_scales"]
