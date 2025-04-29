from typing import Optional


class CDBService:
    @classmethod
    async def init(cls):
        from .database.user import CUserDB
        from .database.userItem import CUserItemDB
        from .database.userPlant import CUserPlantDB
        from .database.userSeed import CUserSeedDB
        from .database.userSoil import CUserSoilDB
        from .database.userSteal import CUserStealDB

        cls.user = CUserDB()
        await cls.user.initDB()

        cls.userSoil = CUserSoilDB()
        await cls.userSoil.initDB()

        cls.userPlant = CUserPlantDB()
        await cls.userPlant.initDB()

        cls.userSeed = CUserSeedDB()
        await cls.userSeed.initDB()

        cls.userItem = CUserItemDB()
        await cls.userItem.initDB()

        cls.userSteal = CUserStealDB()
        await cls.userSteal.initDB()

        #迁移旧数据库
        await cls.userSoil.migrateOldFarmData()

g_pDBService = CDBService()
