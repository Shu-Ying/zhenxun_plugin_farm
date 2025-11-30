from typing import Any, Optional

from zhenxun.services.log import logger


class CDBServiceLocator:
    """
    数据库服务定位器
    负责管理所有数据库服务实例，提供统一的访问接口
    """

    m_pInstance: Optional["CDBServiceLocator"] = None

    def __init__(self):
        self.m_pServices: dict[str, Any] = {}
        self.m_bInitialized = False

    @classmethod
    def getInstance(cls) -> "CDBServiceLocator":
        """
        获取单例实例
        """
        if cls.m_pInstance is None:
            cls.m_pInstance = cls()
        return cls.m_pInstance

    def register(self, name: str, service: Any) -> None:
        """
        注册服务实例
        """
        if name in self.m_pServices:
            logger.error(f"真寻农场服务 {name} 已经注册")
        self.m_pServices[name] = service

    def get(self, name: str) -> Any:
        """
        获取服务实例
        """
        if name not in self.m_pServices:
            raise KeyError(f"服务 {name} 未注册")
        return self.m_pServices[name]

    def getPlantManager(self):
        return self.get("plant")

    def getUserManager(self):
        return self.get("user")

    def getUserSoilManager(self):
        return self.get("userSoil")

    def getUserPlantManager(self):
        return self.get("userPlant")

    def getUserSeedManager(self):
        return self.get("userSeed")

    def getUserItemManager(self):
        return self.get("userItem")

    def getUserStealManager(self):
        return self.get("userSteal")

    def getUserSignManager(self):
        return self.get("userSign")

    def getUserPlantCountManager(self):
        return self.get("userPlantCount")

    def markInitialized(self):
        """
        标记初始化完成
        """
        self.m_bInitialized = True

    @property
    def initialized(self) -> bool:
        """
        检查是否已初始化
        """
        return self.m_bInitialized


# 全局服务定位器实例
g_pDBlocator = CDBServiceLocator.getInstance()
