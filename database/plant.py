import os
import re
from contextlib import asynccontextmanager

import aiosqlite

from zhenxun.services.log import logger

from ..config import g_sPlantPath


class CPlantManager:
    def __init__(self):
        try:
            os.mkdir(g_sPlantPath)
        except FileExistsError:
            pass

    @classmethod
    async def cleanup(cls):
        if hasattr(cls, "m_pDB") and cls.m_pDB:
            await cls.m_pDB.close()

    @classmethod
    async def init(cls) -> bool:
        try:
            _ = os.path.exists(g_sPlantPath)
            cls.m_pDB = await aiosqlite.connect(str(g_sPlantPath))
            cls.m_pDB.row_factory = aiosqlite.Row
            return True
        except Exception as e:
            logger.warning("初始化植物数据库失败", e=e)
            return False

    @classmethod
    @asynccontextmanager
    async def _transaction(cls):
        await cls.m_pDB.execute("BEGIN;")
        try:
            yield
        except:
            await cls.m_pDB.execute("ROLLBACK;")
            raise
        else:
            await cls.m_pDB.execute("COMMIT;")

    @classmethod
    async def executeDB(cls, command: str) -> bool:
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
            async with cls._transaction():
                await cls.m_pDB.execute(command)
            return True
        except Exception as e:
            logger.warning(f"数据库语句执行出错: {command}", e=e)
            return False


    @classmethod
    async def getPlantByName(cls, name: str) -> dict | None:
        """根据作物名称查询记录

        Args:
            name (str): 作物名称

        Returns:
            dict | None: 返回记录字典，未找到返回None
        """
        try:
            async with cls.m_pDB.execute(
                "SELECT * FROM plant WHERE name = ?", (name,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.warning(f"查询作物失败: {name}", e=e)
            return None

    @classmethod
    async def existsPlant(cls, name: str) -> bool:
        """判断作物是否存在

        Args:
            name (str): 作物名称

        Returns:
            bool: 存在返回True，否则False
        """
        try:
            async with cls.m_pDB.execute(
                "SELECT 1 FROM plant WHERE name = ? LIMIT 1", (name,)
            ) as cursor:
                row = await cursor.fetchone()
                return True if row else False
        except Exception as e:
            logger.warning(f"检查作物存在性失败: {name}", e=e)
            return False

    @classmethod
    async def countPlants(cls, onlyBuy: bool = False) -> int:
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
            async with cls.m_pDB.execute(sql, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.warning(f"统计作物数量失败, onlyBuy={onlyBuy}", e=e)
            return 0

    @classmethod
    async def listPlants(cls) -> list[dict]:
        """查询所有作物记录"""
        try:
            async with cls.m_pDB.execute("SELECT * FROM plant ORDER BY level") as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.warning("查询所有作物失败", e=e)
            return []
