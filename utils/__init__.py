from . import utils


def getConfig():
    from . import config

    return config


def getDrawFarm():
    from .darw.drawFarm import CDarwFarm

    return CDarwFarm


def getRequestManager():
    from .request import CRequestManager

    return CRequestManager


def getToolManager():
    from .tool import CToolManager

    return CToolManager


def getJsonManager():
    from .json import g_pJsonManager

    return g_pJsonManager


__all__ = [
    "getConfig",
    "getDrawFarm",
    "getJsonManager",
    "getRequestManager",
    "getToolManager",
    "utils",
]
