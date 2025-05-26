import calendar
from datetime import date, datetime, timedelta
from typing import Optional

from zhenxun.services.log import logger
from zhenxun.utils._build_image import BuildImage

from ..dbService import g_pDBService
from ..json import g_pJsonManager
from .database import CSqlManager


class CUserSignDB(CSqlManager):
    @classmethod
    async def initDB(cls):
        #userSignLog 表结构，每条为一次签到事件
        userSignLog = {
            "uid": "TEXT NOT NULL",                                                #用户ID
            "signDate": "DATE NOT NULL",                                           #签到日期
            "isSupplement": "TINYINT NOT NULL DEFAULT 0",                          #是否补签
            "rewardType": "VARCHAR(20) DEFAULT ''",                                #奖励类型
            "createdAt": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",            #创建时间
            "PRIMARY KEY": "(uid, signDate)"
        }

        #userSignSummary 表结构，每用户一行用于缓存签到状态
        userSignSummary = {
            "uid": "TEXT PRIMARY KEY NOT NULL",                                    #用户ID
            "totalSignDays": "INT NOT NULL DEFAULT 0",                             #累计签到天数
            "currentMonth": "CHAR(7) NOT NULL DEFAULT ''",                         #当前月份（如2025-05）
            "monthSignDays": "INT NOT NULL DEFAULT 0",                             #本月签到次数
            "lastSignDate": "DATE DEFAULT NULL",                                   #上次签到日期
            "continuousDays": "INT NOT NULL DEFAULT 0",                            #连续签到天数
            "supplementCount": "INT NOT NULL DEFAULT 0",                           #补签次数
            "updatedAt": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",            #更新时间
        }

        await cls.ensureTableSchema("userSignLog", userSignLog)
        await cls.ensureTableSchema("userSignSummary", userSignSummary)

    @classmethod
    async def getUserSignCountByDate(cls, uid: str, monthStr: str) -> int:
        """

        Args:
            uid (str): 用户Uid
            monthStr (str): 需要查询的日期 示例: 2025-05

        Returns:
            int: _description_
        """
        try:
            sql = "SELECT COUNT(*) FROM userSignLog WHERE uid=? AND signDate LIKE ?"
            param = f"{monthStr}-%"
            async with cls.m_pDB.execute(sql, (uid, param)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.warning("统计用户月签到次数失败", e=e)
            return 0

    @classmethod
    async def hasSigned(cls, uid: str, signDate: str) -> bool:
        """判断指定日期是否已签到

        Args:
            uid (int): 用户ID
            signDate (str): 日期字符串 'YYYY-MM-DD'

        Returns:
            bool: True=已签到，False=未签到
        """
        try:
            sql = "SELECT 1 FROM userSignLog WHERE uid=? AND signDate=? LIMIT 1"
            async with cls.m_pDB.execute(sql, (uid, signDate)) as cursor:
                row = await cursor.fetchone()
                return row is not None
        except Exception as e:
            logger.warning("查询是否已签到失败", e=e)
            return False

    @classmethod
    async def sign(cls, uid: str, signDate: str = '') -> bool:
        try:
            if not signDate:
                signDate = date.today().strftime("%Y-%m-%d")

            if await cls.hasSigned(uid, signDate):
                return False

            todayStr = date.today().strftime("%Y-%m-%d")
            isSupplement = 0 if signDate == todayStr else 1

            async with cls._transaction():
                await cls.m_pDB.execute(
                    "INSERT INTO userSignLog (uid, signDate, isSupplement, rewardType) VALUES (?, ?, ?, '')",
                    (uid, signDate, isSupplement)
                )

                cursor = await cls.m_pDB.execute("SELECT * FROM userSignSummary WHERE uid=?", (uid,))
                row = await cursor.fetchone()

                currentMonth = signDate[:7]
                if row:
                    monthSignDays = row['monthSignDays'] + 1 if row['currentMonth'] == currentMonth else 1
                    lastDate = row['lastSignDate']
                    prevDate = (datetime.strptime(signDate, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
                    continuousDays = row['continuousDays'] + 1 if lastDate == prevDate else 1
                    supplementCount = row['supplementCount'] + 1 if isSupplement else row['supplementCount']
                    await cls.m_pDB.execute(
                        """
                        UPDATE userSignSummary
                        SET totalSignDays=totalSignDays+1,
                            currentMonth=?,
                            monthSignDays=?,
                            lastSignDate=?,
                            continuousDays=?,
                            supplementCount=?
                        WHERE uid=?
                        """,
                        (currentMonth, monthSignDays, signDate, continuousDays, supplementCount, uid)
                    )
                else:
                    await cls.m_pDB.execute(
                        """
                        INSERT INTO userSignSummary
                        (uid, totalSignDays, currentMonth, monthSignDays, lastSignDate, continuousDays, supplementCount)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (uid, 1, currentMonth, 1, signDate, 1, 1 if isSupplement else 0)
                    )
            return True
        except Exception as e:
            logger.warning("执行签到失败", e=e)
            return False

    @classmethod
    async def drawSignCalendarImage(cls, uid: str, year: int, month: int):
        #绘制签到图，自动提取数据库中该用户该月的签到天数
        cellSize = 80
        padding = 40
        titleHeight = 80
        cols = 7
        rows = 6
        width = cellSize * cols + padding * 2
        height = cellSize * rows + padding * 2 + titleHeight

        img = BuildImage(width, height, color=(255, 255, 255))
        await img.text((padding, 20), f"{year}年{month}月签到表", font_size=36)

        firstWeekday, totalDays = calendar.monthrange(year, month)
        monthStr = f"{year:04d}-{month:02d}"
        try:
            sql = "SELECT signDate FROM userSignLog WHERE uid=? AND signDate LIKE ?"
            async with cls.m_pDB.execute(sql, (uid, f"{monthStr}-%")) as cursor:
                rows = await cursor.fetchall()
                signedDays = set(int(r[0][-2:]) for r in rows if r[0][-2:].isdigit())
        except Exception as e:
            logger.warning("绘制签到图时数据库查询失败", e=e)
            signedDays = set()

        for day in range(1, totalDays + 1):
            index = day + firstWeekday - 1
            row = index // cols
            col = index % cols
            x1 = padding + col * cellSize
            y1 = padding + titleHeight + row * cellSize
            x2 = x1 + cellSize - 10
            y2 = y1 + cellSize - 10
            color = (112, 196, 112) if day in signedDays else (220, 220, 220)
            await img.rectangle((x1, y1, x2, y2), fill=color, outline="black", width=2)
            await img.text((x1 + 10, y1 + 10), str(day), font_size=24)

        return img
