from enum import Enum
from typing import Any


# 活动类型枚举
class ActivityType(Enum):
    PLANTING = "planting"  # 种植活动
    HARVESTING = "harvesting"  # 收获活动
    FISHING = "fishing"  # 钓鱼活动
    COMBAT = "combat"  # 战斗活动


# 效果类型枚举
class EffectType(Enum):
    MULTIPLIER = "multiplier"  # 倍数加成
    FIXED_BONUS = "fixed_bonus"  # 固定加成
    BUFF_APPLICATION = "buff_application"  # 施加BUFF
    QUEST_TRIGGER = "quest_trigger"  # 任务触发


class EffectHandler:
    """
    效果处理器基类
    """

    def execute(self, params: dict, uid: str, context: dict) -> Any:
        raise NotImplementedError


class MultiplierHandler(EffectHandler):
    """
    倍数效果处理器
    """

    def execute(self, params: dict, uid: str, context: dict) -> float:
        base_value = context.get("base_value", 0)
        multiplier = params.get("value", 1.0)

        # 检查条件
        if self._check_conditions(params.get("conditions", {}), player):
            result = base_value * multiplier
            print(f"倍数效果: {base_value} × {multiplier} = {result}")
            return result
        return base_value

    def _check_conditions(self, conditions: dict, player: Player) -> bool:
        """检查生效条件"""
        # 等级要求
        min_level = conditions.get("min_level", 0)
        if player.level < min_level:
            return False

        # 需要特定物品
        required_items = conditions.get("required_items", [])
        for item in required_items:
            if player.inventory.get(item, 0) <= 0:
                return False

        return True


class FixedBonusHandler(EffectHandler):
    """固定加成处理器"""

    def execute(self, params: dict, player: Player, context: dict) -> int:
        base_value = context.get("base_value", 0)
        bonus = params.get("value", 0)

        result = base_value + bonus
        print(f"固定加成: {base_value} + {bonus} = {result}")
        return result


class BuffApplicationHandler(EffectHandler):
    """BUFF应用处理器"""

    def execute(self, params: dict, player: Player, context: dict) -> None:
        buff_id = params["buff_id"]
        duration = params.get("duration", 3600)  # 默认1小时
        properties = params.get("properties", {})

        player.add_buff(buff_id, duration, properties)

        # 立即应用BUFF效果（如果有）
        if "immediate_effect" in params:
            self._apply_immediate_effect(params["immediate_effect"], player)


class QuestTriggerHandler(EffectHandler):
    """任务触发处理器"""

    def execute(self, params: dict, player: Player, context: dict) -> None:
        quest_id = params["quest_id"]
        print(f"为玩家 {player.player_id} 触发任务: {quest_id}")
        # 这里会调用任务系统来分配任务
