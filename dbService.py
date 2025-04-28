from typing import Optional

from .database.user import CUserDB
from .database.userItem import CUserItemDB
from .database.userPlant import CUserPlantDB
from .database.userSeed import CUserSeedDB
from .database.userSoil import CUserSoilDB
from .database.userSteal import CUserStealDB


class CDBService:
    def __init__(self):
        user: Optional["CUserDB"] = None
        userSoil: Optional["CUserSoilDB"] = None
        userPlant: Optional["CUserPlantDB"] = None
        userSeed: Optional["CUserSeedDB"] = None
        userItem: Optional["CUserItemDB"] = None
        userSteal: Optional["CUserStealDB"] = None

    @classmethod
    async def init(cls):
        cls.user = CUserDB()
        cls.userSoil = CUserSoilDB()
        cls.userPlant = CUserPlantDB()
        cls.userSeed = CUserSeedDB()
        cls.userItem = CUserItemDB()
        cls.userSteal = CUserStealDB()

g_pDBService = CDBService()
