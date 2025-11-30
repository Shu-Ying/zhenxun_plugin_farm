from abc import ABC
from contextlib import asynccontextmanager
import os
from pathlib import Path
import re
from typing import Any, ClassVar

import aiosqlite

from zhenxun.services.log import logger

from ...utils import config
from .dbServiceLocator import g_pDBlocator


class CSqlManager(ABC):
    """
    数据库管理器基类
    所有具体的数据管理器都应该继承这个类
    """

    m_pDB: ClassVar[aiosqlite.Connection | None] = None

    def __init__(self):
        self.m_sTableName: str | None = None
        self.m_bInitialized: bool = False

        self.m_pDBPath = Path(config.g_sDBPath)
        if self.m_pDBPath and not self.m_pDBPath.exists():
            os.makedirs(self.m_pDBPath, exist_ok=True)

    @classmethod
    async def init(cls) -> bool:
        try:
            if cls.m_pDB is None:
                cls.m_pDB = await aiosqlite.connect(config.g_sDBFilePath)
                cls.m_pDB.row_factory = aiosqlite.Row
                logger.info("真寻农场数据库连接初始化成功")
                return True
            else:
                logger.info("真寻农场数据库连接已存在，跳过初始化")
                return True
        except Exception as e:
            logger.error(f"真寻农场数据库连接初始化失败: {e}")
            return False

    @classmethod
    async def cleanup(cls):
        if cls.m_pDB:
            await cls.m_pDB.close()
            cls.m_pDB = None
            logger.info("真寻农场数据库连接已关闭")

    @classmethod
    def getDB(cls) -> aiosqlite.Connection:
        if cls.m_pDB is None:
            raise RuntimeError("数据库连接未初始化，请先调用 init_global_db()")
        return cls.m_pDB

    @classmethod
    def getPlantManager(cls) -> Any:
        return g_pDBlocator.getPlantManager()

    @classmethod
    def getUserManager(cls) -> Any:
        return g_pDBlocator.getUserManager()

    @classmethod
    def getUserSoilManager(cls) -> Any:
        return g_pDBlocator.getUserSoilManager()

    @classmethod
    def getUserSeedManager(cls) -> Any:
        return g_pDBlocator.getUserSeedManager()

    @classmethod
    def getUserItemManager(cls) -> Any:
        return g_pDBlocator.getUserItemManager()

    @classmethod
    def getUserStealManager(cls) -> Any:
        return g_pDBlocator.getUserStealManager()

    @classmethod
    def getUserSignManager(cls) -> Any:
        return g_pDBlocator.getUserSignManager()

    @classmethod
    def getUserPlantCountManager(cls) -> Any:
        return g_pDBlocator.getUserPlantCountManager()

    def isInitialized(self) -> bool:
        """检查是否已初始化"""
        return self.m_bInitialized

    def setInitialized(self) -> None:
        """标记为已初始化"""
        self.m_bInitialized = True

    @classmethod
    @asynccontextmanager
    async def _transaction(cls):
        await cls.getDB().execute("BEGIN;")
        try:
            yield
        except:
            await cls.getDB().execute("ROLLBACK;")
            raise
        else:
            await cls.getDB().execute("COMMIT;")

    @classmethod
    async def getTableInfo(cls, tableName: str) -> list:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tableName):
            raise ValueError(f"Illegal table name: {tableName}")
        try:
            cursor = await cls.getDB().execute(f'PRAGMA table_info("{tableName}")')
            rows = await cursor.fetchall()
            return [{"name": row[1], "type": row[2]} for row in rows]
        except aiosqlite.Error:
            return []

    # @classmethod
    # async def ensureTableSchema(cls, tableName: str, columns: dict) -> bool:
    #     """由AI生成
    #     创建表或为已存在表添加缺失字段。
    #     返回 True 表示有变更（创建或新增列），False 则无操作

    #     Args:
    #         tableName (str): 表名
    #         columns (dict): 字典

    #     Returns:
    #         bool:
    #     """

    #     info = await cls.getTableInfo(tableName)
    #     existing = {col["name"]: col["type"].upper() for col in info}
    #     desired = {k: v.upper() for k, v in columns.items() if k != "PRIMARY KEY"}
    #     primaryKey = columns.get("PRIMARY KEY", "")

    #     if not existing:
    #         colsDef = ", ".join(f'"{k}" {v}' for k, v in desired.items())
    #         if primaryKey:
    #             colsDef += f", PRIMARY KEY {primaryKey}"
    #         await cls.getDB().execute(f'CREATE TABLE "{tableName}" ({colsDef});')
    #         return True

    #     toAdd = [k for k in desired if k not in existing]
    #     toRemove = [k for k in existing if k not in desired]
    #     typeMismatch = [
    #         k for k in desired if k in existing and existing[k] != desired[k]
    #     ]

    #     if toAdd and not toRemove and not typeMismatch:
    #         for col in toAdd:
    #             await cls.getDB().execute(
    #                 f'ALTER TABLE "{tableName}" ADD COLUMN "{col}" {columns[col]}'
    #             )
    #         return True

    #     async with cls._transaction():
    #         tmpTable = f"{tableName}_new"
    #         colsDef = ", ".join(f'"{k}" {v}' for k, v in desired.items())
    #         if primaryKey:
    #             colsDef += f", PRIMARY KEY {primaryKey}"
    #         await cls.getDB().execute(f'CREATE TABLE "{tmpTable}" ({colsDef});')

    #         commonCols = [k for k in desired if k in existing]
    #         if commonCols:
    #             colsStr = ", ".join(f'"{c}"' for c in commonCols)

    #             sql = (
    #                 f'INSERT INTO "{tmpTable}" ({colsStr}) '
    #                 f"SELECT {colsStr} "
    #                 f'FROM "{tableName}";'
    #             )

    #             await cls.getDB().execute(sql)
    #         await cls.getDB().execute(f'DROP TABLE "{tableName}";')
    #         await cls.getDB().execute(
    #             f'ALTER TABLE "{tmpTable}" RENAME TO "{tableName}";'
    #         )
    #     return True

    @classmethod
    async def ensureTableSchema(cls, tableName: str, columns: dict) -> bool:
        """由AI生成
        创建表或为已存在表添加缺失字段。
        返回 True 表示有变更（创建或新增列），False 则无操作

        Args:
            tableName (str): 表名
            columns (dict): 字典

        Returns:
            bool:
        """
        info = await cls.getTableInfo(tableName)
        existing = {col["name"]: col["type"].upper() for col in info}
        desired = {k: v.upper() for k, v in columns.items() if k != "PRIMARY KEY"}
        primaryKey = columns.get("PRIMARY KEY", "")

        if not existing:
            colsDef = ", ".join(f'"{k}" {v}' for k, v in desired.items())
            if primaryKey:
                colsDef += f", PRIMARY KEY {primaryKey}"
            await cls.getDB().execute(f'CREATE TABLE "{tableName}" ({colsDef});')
            return True

        toAdd = [k for k in desired if k not in existing]
        toRemove = [k for k in existing if k not in desired]
        typeMismatch = [
            k for k in desired if k in existing and existing[k] != desired[k]
        ]

        if toRemove or typeMismatch:
            return False

        if toAdd:
            for col in toAdd:
                try:
                    await cls.getDB().execute(
                        f'ALTER TABLE "{tableName}" ADD COLUMN "{col}" {columns[col]}'
                    )
                except aiosqlite.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        continue
                    else:
                        raise
            return True

        return False

    @classmethod
    async def executeDB(cls, command: str) -> bool:
        """执行自定义SQL

        Args:
            command (str): SQL语句

        Returns:
            bool: 是否执行成功
        """
        if not command:
            return False

        try:
            async with cls._transaction():
                await cls.getDB().execute(command)
            return True
        except Exception:
            return False

    @classmethod
    async def insert(cls, tableName: str, data: dict) -> bool:
        """
        插入数据

        Args:
            tableName: 表名
            data: 要插入的数据字典，键为字段名，值为字段值

        Returns:
            bool: 是否执行成功
        """
        if not data:
            return False

        try:
            # 构建参数化查询
            columns = ", ".join(f'"{k}"' for k in data.keys())
            placeholders = ", ".join("?" for _ in data.keys())
            values = list(data.values())

            sql = f'INSERT INTO "{tableName}" ({columns}) VALUES ({placeholders})'

            async with cls._transaction():
                await cls.getDB().execute(sql, values)
            return True
        except Exception as e:
            logger.debug("真寻农场插入数据失败！", e=e)
            return False

    @classmethod
    async def batch_insert(cls, tableName: str, data_list: list) -> bool:
        """
        批量插入数据

        Args:
            tableName: 表名
            data_list: 要插入的数据字典列表

        Returns:
            bool: 是否执行成功
        """
        if not data_list:
            return False

        try:
            # 使用第一个字典的键作为所有记录的字段
            columns = ", ".join(f'"{k}"' for k in data_list[0].keys())
            placeholders = ", ".join("?" for _ in data_list[0].keys())

            sql = f'INSERT INTO "{tableName}" ({columns}) VALUES ({placeholders})'

            async with cls._transaction():
                await cls.getDB().executemany(
                    sql, [list(data.values()) for data in data_list]
                )
            return True
        except Exception as e:
            logger.debug("真寻农场批量插入数据失败！", e=e)
            return False

    @classmethod
    async def select(
        cls,
        tableName: str,
        columns: list[Any] | None = None,
        where: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """
        查询数据

        Args:
            tableName: 表名
            columns: 要查询的字段列表，None表示所有字段
            where: 查询条件字典
            order_by: 排序字段
            limit: 限制返回记录数

        Returns:
            list: 查询结果列表，每个元素是一个字典
        """
        try:
            # 构建SELECT部分
            if columns:
                select_clause = ", ".join(f'"{col}"' for col in columns)
            else:
                select_clause = "*"

            sql = f'SELECT {select_clause} FROM "{tableName}"'

            # 构建WHERE部分
            params = []
            if where:
                where_conditions = []
                for key, value in where.items():
                    if isinstance(value, (list, tuple)):
                        # 处理IN查询
                        placeholders = ", ".join("?" for _ in value)
                        where_conditions.append(f'"{key}" IN ({placeholders})')
                        params.extend(value)
                    else:
                        where_conditions.append(f'"{key}" = ?')
                        params.append(value)

                if where_conditions:
                    sql += " WHERE " + " AND ".join(where_conditions)

            # 构建ORDER BY部分
            if order_by:
                sql += f" ORDER BY {order_by}"

            # 构建LIMIT部分
            if limit:
                sql += f" LIMIT {limit}"

            cursor = await cls.getDB().execute(sql, params)
            rows = await cursor.fetchall()

            # 转换为字典列表
            result = []
            for row in rows:
                result.append(dict(row))

            return result
        except Exception as e:
            logger.debug("真寻农场查询数据失败！", e=e)
            return []

    @classmethod
    async def update(cls, tableName: str, data: dict, where: dict) -> bool:
        """
        更新数据

        Args:
            tableName: 表名
            data: 要更新的数据字典
            where: 更新条件字典

        Returns:
            bool: 是否执行成功
        """
        if not data:
            return False

        if not where:
            return False

        try:
            # 构建SET部分
            set_conditions = []
            params = []
            for key, value in data.items():
                set_conditions.append(f'"{key}" = ?')
                params.append(value)

            # 构建WHERE部分
            where_conditions = []
            for key, value in where.items():
                where_conditions.append(f'"{key}" = ?')
                params.append(value)

            sql = f'UPDATE "{tableName}" SET {", ".join(set_conditions)} WHERE {" AND ".join(where_conditions)}'

            async with cls._transaction():
                cursor = await cls.getDB().execute(sql, params)
                # 检查是否影响了行
                return cursor.rowcount > 0
        except Exception as e:
            logger.debug("真寻农场更新数据失败！", e=e)
            return False

    @classmethod
    async def delete(cls, tableName: str, where: dict) -> bool:
        """
        删除数据

        Args:
            tableName: 表名
            where: 删除条件字典

        Returns:
            bool: 是否执行成功
        """
        if not where:
            return False

        try:
            # 构建WHERE部分
            where_conditions = []
            params = []
            for key, value in where.items():
                where_conditions.append(f'"{key}" = ?')
                params.append(value)

            sql = f'DELETE FROM "{tableName}" WHERE {" AND ".join(where_conditions)}'

            async with cls._transaction():
                cursor = await cls.getDB().execute(sql, params)
                # 检查是否影响了行
                return cursor.rowcount > 0
        except Exception as e:
            logger.debug("真寻农场删除数据失败！", e=e)
            return False

    @classmethod
    async def exists(cls, tableName: str, where: dict) -> bool:
        """
        检查记录是否存在

        Args:
            tableName: 表名
            where: 查询条件字典

        Returns:
            bool: 是否存在符合条件的记录
        """
        try:
            result = await cls.select(tableName, columns=["1"], where=where, limit=1)
            return len(result) > 0
        except Exception as e:
            logger.debug("真寻农场检查数据失败！", e=e)
            return False

    @classmethod
    async def count(cls, tableName: str, where: dict = {}) -> int:
        """
        统计记录数量

        Args:
            tableName: 表名
            where: 查询条件字典

        Returns:
            int: 记录数量
        """
        try:
            # 构建WHERE部分
            sql = f'SELECT COUNT(*) as count FROM "{tableName}"'
            params = []

            if where:
                where_conditions = []
                for key, value in where.items():
                    where_conditions.append(f'"{key}" = ?')
                    params.append(value)

                sql += " WHERE " + " AND ".join(where_conditions)

            cursor = await cls.getDB().execute(sql, params)
            row = await cursor.fetchone()
            return row["count"] if row else 0
        except Exception as e:
            logger.debug("真寻农场统计数据失败！", e=e)
            return 0


g_pSqlManager = CSqlManager()
