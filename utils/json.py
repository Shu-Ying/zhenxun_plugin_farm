import json

from zhenxun.services.log import logger

from . import config
from .request import g_pRequestManager


class CJsonManager:
    def __init__(self):
        self._m_pItem = {}
        self._m_pLevel = {}
        self._m_pSoil = {}
        self._m_pSign = {}

        self._m_bItemLoaded = False
        self._m_bLevelLoaded = False
        self._m_bSoilLoaded = False
        self._m_bSignLoaded = False

    async def getItem(self) -> dict:
        if not self._m_bItemLoaded:
            success = await self.initItem()
            if not success:
                return {}
        return self._m_pItem

    async def getLevel(self) -> dict:
        if not self._m_bLevelLoaded:
            success = await self.initLevel()
            if not success:
                return {}
        return self._m_pLevel

    async def getSoil(self) -> dict:
        if not self._m_bSoilLoaded:
            success = await self.initSoil()
            if not success:
                return {}
        return self._m_pSoil

    async def getSign(self) -> dict:
        if not self._m_bSignLoaded:
            success = await self.initSign()
            if not success:
                return {}
        return self._m_pSign

    async def reloadItem(self) -> bool:
        self._m_bItemLoaded = False
        return await self.initItem()

    async def reloadLevel(self) -> bool:
        self._m_bLevelLoaded = False
        return await self.initLevel()

    async def reloadSoil(self) -> bool:
        self._m_bSoilLoaded = False
        return await self.initSoil()

    async def reloadSign(self) -> bool:
        self._m_bSignLoaded = False
        return await self.initSign()

    async def initItem(self) -> bool:
        try:
            with open(
                config.g_sConfigPath / "item.json",
                encoding="utf-8",
            ) as file:
                self._m_pItem = json.load(file)
                self._m_bItemLoaded = True
                return True
        except FileNotFoundError:
            logger.warning("item.json 打开失败")
            self._m_pItem = {}
            return False
        except json.JSONDecodeError as e:
            logger.warning(f"item.json JSON格式错误: {e}")
            self._m_pItem = {}
            return False

    async def initLevel(self) -> bool:
        try:
            with open(
                config.g_sConfigPath / "level.json",
                encoding="utf-8",
            ) as file:
                self._m_pLevel = json.load(file)
                self._m_bLevelLoaded = True
                return True
        except FileNotFoundError:
            logger.warning("level.json 打开失败")
            self._m_pLevel = {}
            return False
        except json.JSONDecodeError as e:
            logger.warning(f"level.json JSON格式错误: {e}")
            self._m_pLevel = {}
            return False

    async def initSoil(self) -> bool:
        try:
            with open(
                config.g_sConfigPath / "soil.json",
                encoding="utf-8",
            ) as file:
                self._m_pSoil = json.load(file)
                self._m_bSoilLoaded = True
                return True
        except FileNotFoundError:
            logger.warning("soil.json 打开失败")
            self._m_pSoil = {}
            return False
        except json.JSONDecodeError as e:
            logger.warning(f"soil.json JSON格式错误: {e}")
            self._m_pSoil = {}
            return False

    async def initSignInFile(self) -> bool:
        if not await g_pRequestManager.initSignInFile():
            config.g_bSignStatus = False
            return False
        else:
            result = await self.initSign()
            config.g_bSignStatus = result
            return result

    async def initSign(self) -> bool:
        try:
            with open(
                config.g_sSignInPath,
                encoding="utf-8",
            ) as file:
                self._m_pSign = json.load(file)
                self._m_bSignLoaded = True
                return True
        except FileNotFoundError:
            logger.warning("sign_in.json 打开失败")
            self._m_pSign = {}
            return False
        except json.JSONDecodeError as e:
            logger.warning(f"sign_in.json JSON格式错误: {e}")
            self._m_pSign = {}
            return False


g_pJsonManager = CJsonManager()
