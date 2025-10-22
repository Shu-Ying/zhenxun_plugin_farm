class CDBService:
    async def init(self):
        from .database.plant import CPlantManager
        from .database.user import CUserDB
        from .database.userItem import CUserItemDB
        from .database.userPlant import CUserPlantDB
        from .database.userSeed import CUserSeedDB
        from .database.userSign import CUserSignDB
        from .database.userSoil import CUserSoilDB
        from .database.userSteal import CUserStealDB

        self.plant = CPlantManager()
        await self.plant.init()

        self.user = CUserDB()
        await self.user.initDB()

        self.userSoil = CUserSoilDB()
        await self.userSoil.initDB()

        self.userPlant = CUserPlantDB()
        await self.userPlant.initDB()

        self.userSeed = CUserSeedDB()
        await self.userSeed.initDB()

        self.userItem = CUserItemDB()
        await self.userItem.initDB()

        self.userSteal = CUserStealDB()
        await self.userSteal.initDB()

        self.userSign = CUserSignDB()
        await self.userSign.initDB()

    async def cleanup(self):
        await self.plant.cleanup()


g_pDBService = CDBService()
