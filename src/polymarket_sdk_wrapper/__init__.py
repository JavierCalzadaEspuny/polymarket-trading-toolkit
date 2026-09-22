"""Small wrappers around Polymarket's public API surfaces."""

__version__ = "0.1.0"

from .gamma import GammaEvent, token

__all__ = ["GammaEvent", "__version__", "token"]
