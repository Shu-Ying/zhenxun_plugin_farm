from contextlib import asynccontextmanager
import os

import aiosqlite

from zhenxun.configs.config import Config
from zhenxun.services.log import logger

from ...utils import config, getRequestManager


class CPlantManager:
    def __init__(self):
        self.m_sTableName = "plant"
        self.m_bInitialized = False

        try:
            os.mkdir(config.g_sPlantPath)
        except FileExistsError:
            pass

    async def cleanup(self):
        if hasattr(self, "m_pDB") and self.m_pDB:
            await self.m_pDB.close()

    async def init(self) -> bool:
        try:
            _ = os.path.exists(config.g_sPlantPath)

            if config.g_bIsDebug:
                self.m_pDB = await aiosqlite.connect(
                    str(config.g_sPlantPath.parent / "plant-test.db")
                )
            else:
                self.m_pDB = await aiosqlite.connect(str(config.g_sPlantPath))

            self.m_pDB.row_factory = aiosqlite.Row
            return True
        except Exception as e:
            logger.warning("初始化植物数据库失败", e=e)
            return False

    async def initDB(self):
        self.m_bInitialized = True

    @asynccontextmanager
    async def _transaction(self):
        await self.m_pDB.execute("BEGIN;")
        try:
            yield
        except:
            await self.m_pDB.execute("ROLLBACK;")
            raise
        else:
            await self.m_pDB.execute("COMMIT;")

    async def executeDB(self, command: str) -> bool:
        """执行自定义SQL

        Args:
            command (str): SQL语句

        Returns:
            bool: 是否执行成功
        """
        if not command:
            logger.warning("数据库语句长度为空！")
            return False

        try:
            async with self._transaction():
                await self.m_pDB.execute(command)
            return True
        except Exception as e:
            logger.warning(f"数据库语句执行出错: {command}", e=e)
            return False

    async def getPlantByName(self, name: str) -> dict | None:
        """根据作物名称查询记录

        Args:
            name (str): 作物名称

        Returns:
            dict | None: 返回记录字典，未找到返回None
        """
        try:
            async with self.m_pDB.execute(
                "SELECT * FROM plant WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning(f"查询作物失败: {name}", e=e)
            return None

    async def getPlantPhaseByName(self, name: str) -> list[int]:
        """根据作物名称获取作物各个阶段

        Args:
            name (str): 作物名称

        Returns:
            list: 阶段数组
        """
        try:
            async with self.m_pDB.execute(
                "SELECT phase FROM plant WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()

                if not row:
                    return []

                phase = row[0].split(",")

                seen = set()
                result = []

                for x in phase:
                    num = int(x)

                    if num not in seen:
                        seen.add(num)
                        result.append(num)

                return result
        except Exception as e:
            logger.warning(f"查询作物阶段失败: {name}", e=e)
            return []

    async def getPlantPhaseNumberByName(self, name: str) -> int:
        """根据作物名称获取作物总阶段数

        Args:
            name (str): 作物名称

        Returns:
            int: 总阶段数
        """
        try:
            async with self.m_pDB.execute(
                "SELECT phase FROM plant WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()

                if not row:
                    return -1

                phase = row[0].split(",")

                # 去重
                seen = set()
                result = []
                for x in phase:
                    if x not in seen:
                        seen.add(x)
                        result.append(x)

                return len(result)
        except Exception as e:
            logger.warning(f"查询作物阶段失败: {name}", e=e)
            return -1

    async def getPlantAgainByName(self, name: str) -> int:
        """根据作物名称获取作物再次成熟时间

        Args:
            name (str): 作物名称

        Returns:
            int: 再次成熟时间 单位:h
        """

        try:
            async with self.m_pDB.execute(
                "SELECT phase FROM plant WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()

                if not row:
                    return -1

                phase = row[0].split(",")
                again = phase[-1] - phase[3] / 60 / 60

                return again

        except Exception as e:
            logger.warning(f"查询作物阶段失败: {name}", e=e)
            return -1

    async def existsPlant(self, name: str) -> bool:
        """判断作物是否存在

        Args:
            name (str): 作物名称

        Returns:
            bool: 存在返回True，否则False
        """
        try:
            async with self.m_pDB.execute(
                "SELECT 1 FROM plant WHERE name = ? LIMIT 1", (name,)
            ) as cursor:
                row = await cursor.fetchone()
                return True if row else False
        except Exception as e:
            logger.warning(f"检查作物存在性失败: {name}", e=e)
            return False

    async def countPlants(self, onlyBuy: bool = False) -> int:
        """获取作物总数

        Args:
            onlyBuy (bool): 若为True，仅统计isBuy=1的记录，默认False

        Returns:
            int: 符合条件的记录数
        """
        try:
            if onlyBuy:
                sql = "SELECT COUNT(*) FROM plant WHERE isBuy = 1"
                params: tuple = ()
            else:
                sql = "SELECT COUNT(*) FROM plant"
                params: tuple = ()
            async with self.m_pDB.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.warning(f"统计作物数量失败, onlyBuy={onlyBuy}", e=e)
            return 0

    async def listPlants(self) -> list[dict]:
        """查询所有作物记录"""
        try:
            async with self.m_pDB.execute(
                "SELECT * FROM plant ORDER BY level"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning("查询所有作物失败", e=e)
            return []

    async def downloadPlant(self) -> bool:
        """遍历所有作物，下载各阶段图片及icon文件到指定文件夹

        Returns:
            bool: 全部下载完成返回True，如有失败返回False
        """
        success = True
        baseUrl = Config.get_config("zhenxun_plugin_farm", "服务地址")

        baseUrl = baseUrl.rstrip("/") + ":8998/file"
        try:
            plants = await self.listPlants()
            for plant in plants:
                name = plant["name"]
                phaseCount = await self.getPlantPhaseNumberByName(name)
                saveDir = os.path.join(config.g_sResourcePath, "plant", name)
                begin = 0 if plant["general"] == 0 else 1

                for idx in range(begin, phaseCount + 1):
                    fileName = f"{idx}.png"
                    fullPath = os.path.join(saveDir, fileName)

                    if os.path.exists(fullPath):
                        continue

                    url = f"{baseUrl}/{name}/{idx}.png"
                    if not await getRequestManager().download(
                        url, saveDir, f"{idx}.png"
                    ):
                        success = False

                iconName = "icon.png"
                iconPath = os.path.join(saveDir, iconName)
                if not os.path.exists(iconPath):
                    iconUrl = f"{baseUrl}/{name}/{iconName}"
                    if not await getRequestManager().download(
                        iconUrl, saveDir, iconName
                    ):
                        success = False

            return success
        except Exception as e:
            logger.warning(f"下载作物资源异常: {e}")
            return False
