import asyncio
from typing import Any

from zhenxun.services.log import logger

from .database import (
    CPlantManager,
    CUserDB,
    CUserItemDB,
    CUserPlantCountDB,
    CUserPlantDB,
    CUserSeedDB,
    CUserSignDB,
    CUserSoilDB,
    CUserStealDB,
    g_pDBlocator,
)


class CDBService:
    """
    数据库服务管理器
    负责初始化和协调所有数据库服务
    """

    def __init__(self):
        self.m_manager: dict[str, Any] = {}
        self.m_bInitialized = False

    async def init(self):
        if self.m_bInitialized:
            logger.warning("真寻农场数据库服务已初始化")
            return

        m_manager = {
            "plant": CPlantManager(),
            "user": CUserDB(),
            "userSoil": CUserSoilDB(),
            "userPlant": CUserPlantDB(),
            "userSeed": CUserSeedDB(),
            "userItem": CUserItemDB(),
            "userSteal": CUserStealDB(),
            "userSign": CUserSignDB(),
            "userPlantCount": CUserPlantCountDB(),
        }

        for name, manager in m_manager.items():
            g_pDBlocator.register(name, manager)
            self.m_manager[name] = manager

        tasks = []
        for name, manager in self.m_manager.items():
            tasks.append(manager.init())
            tasks.append(manager.initDB())

        await asyncio.gather(*tasks)

        g_pDBlocator.markInitialized()
        self.m_bInitialized = True

        logger.debug("真寻农场数据库服务初始化完成")

    async def cleanup(self):
        task = []

        for manager in self.m_manager.values():
            if hasattr(manager, "cleanup"):
                task.append(manager.cleanup())

        await asyncio.gather(*task)
        self.m_manager.clear()
        self.m_bInitialized = False

    @property
    def plant(self):
        return self.m_manager["plant"]

    @property
    def user(self):
        return self.m_manager["user"]

    @property
    def userSoil(self):
        return self.m_manager["userSoil"]

    @property
    def userPlant(self):
        return self.m_manager["userPlant"]

    @property
    def userSeed(self):
        return self.m_manager["userSeed"]

    @property
    def userItem(self):
        return self.m_manager["userItem"]

    @property
    def userSteal(self):
        return self.m_manager["userSteal"]

    @property
    def userSign(self):
        return self.m_manager["userSign"]

    @property
    def userPlantCount(self):
        return self.m_manager["userPlantCount"]

    @property
    def initialized(self) -> bool:
        return self.m_bInitialized


g_pDBService = CDBService()
