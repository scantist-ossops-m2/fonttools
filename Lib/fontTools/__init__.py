import logging
from fontTools.misc.loggingTools import configLogger

log = logging.getLogger(__name__)

version = __version__ = "4.52.5.dev0"

__all__ = ["version", "log", "configLogger"]
