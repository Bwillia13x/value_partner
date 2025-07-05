from .client import ValueInvestClient
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version(__package__ or "valueinvest_sdk")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["ValueInvestClient"]