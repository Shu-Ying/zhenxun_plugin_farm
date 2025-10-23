from datetime import datetime
from typing import Any

from zhenxun.configs.config import Config
from zhenxun.services.log import logger

from ...utils.config import DATA_PATH, g_sResourcePath, g_sTranslation
from ...utils.json import g_pJsonManager
from ...utils.tool import g_pToolManager
from ..dbService import g_pDBService


class CSignInManager:
    async def signInByUid(self, uid: str) -> str:
        toDay = g_pToolManager.dateTime().date().today()
        message = ""
        status = await g_pDBService.userSign.sign(uid, toDay.strftime("%Y-%m-%d"))

        # 如果完成签到
        if status == 1 or status == 2:
            # 获取签到总天数
            signDay = await g_pDBService.userSign.getUserSignCountByDate(
                uid, toDay.strftime("%Y-%m")
            )
            exp, point = await g_pDBService.userSign.getUserSignRewardByDate(
                uid, toDay.strftime("%Y-%m-%d")
            )

            message += g_sTranslation["signIn"]["success"].format(
                day=signDay, exp=exp, num=point
            )

            jSign = await g_pJsonManager.getSign()
            reward = jSign["continuou"].get(f"{signDay}", None)

            signType = Config.get_config("zhenxun_plugin_farm", "签到图片样式")

            if reward:
                extraPoint = reward.get("point", 0)
                extraExp = reward.get("exp", 0)

                plant = reward.get("plant", {})

                message += g_sTranslation["signIn"]["grandTotal"].format(
                    exp=extraExp, num=extraPoint
                )

                vipPoint = reward.get("vipPoint", 0)

                if vipPoint > 0:
                    message += g_sTranslation["signIn"]["grandTotal1"].format(
                        num=vipPoint
                    )

                if plant:
                    for key, value in plant.items():
                        message += g_sTranslation["signIn"]["grandTotal2"].format(
                            name=key, num=value
                        )
        else:
            message = g_sTranslation["signIn"]["error1"]
            pass

        return message

    def generateSignData(
        self,
        todayRewards: list[dict[str, Any]],
        cumulativeRewards: list[dict[str, Any]],
        currentProgress: int,
        totalMilestones: int,
        consecutiveDays: int = 0,
    ) -> dict[str, Any]:
        """生成签到页面所需的数据

        Args:
            todayRewards (list[dict[str, Any]]): 今日奖励列表
            cumulativeRewards (list[dict[str, Any]]): 累计奖励列表
            currentProgress (int): 当前进度
            totalMilestones (int): 总里程碑数
            consecutiveDays (int, optional): 连续签到天数

        Returns:
            dict[str, Any]: 签到数据字典
        """

        # 计算进度百分比
        progressPercentage = min(100, int((currentProgress / totalMilestones) * 100))

        # 计算已达成里程碑数量
        achievedMilestones = 0
        for reward in cumulativeRewards:
            if reward.get("achieved", False):
                achievedMilestones += 1

        return {
            "currentDate": datetime.now().strftime("%Y年%m月%d日"),
            "todayRewards": todayRewards,
            "cumulativeRewards": cumulativeRewards,
            "currentProgress": currentProgress,
            "totalMilestones": totalMilestones,
            "progressPercentage": progressPercentage,
            "achievedMilestones": achievedMilestones,
            "consecutiveDays": consecutiveDays,
        }

    async def createSignImage(
        self,
        todayRewards: list[dict[str, Any]],
        cumulativeRewards: list[dict[str, Any]],
        currentProgress: int,
        totalMilestones: int,
        consecutiveDays: int = 0,
    ):
        """创建签到图片的完整流程

        Args:
            todayRewards (list[dict[str, Any]]): 今日奖励列表
            cumulativeRewards (list[dict[str, Any]]): 累计奖励列表
            currentProgress (int): 当前进度
            totalMilestones (int): 总里程碑数
            consecutiveDays (int, optional): 连续签到天数
        """
        try:
            templatePath = g_sResourcePath / "html/sign_in.html"
            outputPath = g_sResourcePath / "temp_html/sign_in.html"
            savePath = DATA_PATH / "farm_res/html/sign_in.png"

            # 1. 生成渲染数据
            context = self.generateSignData(
                todayRewards=todayRewards,
                cumulativeRewards=cumulativeRewards,
                currentProgress=currentProgress,
                totalMilestones=totalMilestones,
                consecutiveDays=consecutiveDays,
            )

            # 2. 渲染HTML文件
            g_pToolManager.renderHtmlToFile(templatePath, context, outputPath)

            # 3. 生成图片字节数据
            # imageBytes = await g_pToolManager.screenshotHtmlToBytes(outputPath)

            # 4. 保存图片文件
            await g_pToolManager.screenshotSave(
                str(outputPath), str(savePath), 600, 800
            )

        except Exception as e:
            logger.error(f"❌ 生成签到图片时出错: {e}")
            raise


g_pSignInManager = CSignInManager()
