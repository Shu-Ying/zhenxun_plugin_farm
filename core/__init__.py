from .database import g_pDBlocator, g_pSqlManager
from .help import CHelpManager
from .player.player import CPlayer
from .player.playerPool import g_pUserPool
from .shop import CShopManager


def getFarmManager():
    from .farm import CFarmManager

    return CFarmManager()


def getSignInManager():
    from .activity.sign_in import CSignInManager

    return CSignInManager()


__all__ = [
    "CHelpManager",
    "CPlayer",
    "CShopManager",
    "g_pDBlocator",
    "g_pSqlManager",
    "g_pUserPool",
    "getFarmManager",
    "getSignInManager",
]
