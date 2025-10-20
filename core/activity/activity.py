class ActivityManager:
    """活动管理器"""

    def __init__(self):
        self.activities = {}  # 活动ID -> 活动配置
        self.active_activities = set()  # 当前活跃的活动ID
        self.effect_handlers = {}  # 效果类型 -> 处理器

        # 注册效果处理器
        self._register_handlers()

    def _register_handlers(self):
        """注册所有效果处理器"""
        self.effect_handlers[EffectType.MULTIPLIER] = MultiplierHandler()
        self.effect_handlers[EffectType.FIXED_BONUS] = FixedBonusHandler()
        self.effect_handlers[EffectType.BUFF_APPLICATION] = BuffApplicationHandler()
        self.effect_handlers[EffectType.QUEST_TRIGGER] = QuestTriggerHandler()

    def load_activities_from_config(self, config_path: str):
        """从配置文件加载活动"""
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        for activity_data in config["activities"]:
            activity = Activity(activity_data)
            self.activities[activity.id] = activity
            print(f"加载活动: {activity.name}")

    def update_activity_status(self):
        """更新活动状态（定时调用）"""
        now = datetime.now()

        for activity in self.activities.values():
            is_active = activity.start_time <= now <= activity.end_time

            if is_active and activity.id not in self.active_activities:
                # 活动开始
                self.active_activities.add(activity.id)
                print(f"活动开始: {activity.name}")

            elif not is_active and activity.id in self.active_activities:
                # 活动结束
                self.active_activities.remove(activity.id)
                print(f"活动结束: {activity.name}")

    def get_active_activities(self, activity_type: ActivityType = None) -> List:
        """获取当前活跃的活动"""
        active_list = []

        for activity_id in self.active_activities:
            activity = self.activities[activity_id]
            if activity_type is None or activity.activity_type == activity_type:
                active_list.append(activity)

        return active_list

    def apply_activity_effects(
        self,
        activity_type: ActivityType,
        player: Player,
        base_value: int,
        context: Dict = None,
    ) -> int:
        """应用活动效果"""
        if context is None:
            context = {}

        context["base_value"] = base_value
        result = base_value

        # 获取同类型的所有活跃活动
        active_activities = self.get_active_activities(activity_type)

        for activity in active_activities:
            print(f"为玩家 {player.player_id} 应用活动: {activity.name}")

            for effect in activity.effects:
                handler = self.effect_handlers.get(effect.type)
                if handler:
                    try:
                        effect_result = handler.execute(effect.params, player, context)
                        if effect_result is not None:
                            result = effect_result
                            context["base_value"] = result  # 更新基础值供后续效果使用
                    except Exception as e:
                        print(f"效果执行失败: {effect.type}, 错误: {e}")

        return result


class Activity:
    """活动类"""

    def __init__(self, data: Dict):
        self.id = data["id"]
        self.name = data["name"]
        self.activity_type = ActivityType(data["activity_type"])
        self.start_time = datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
        self.end_time = datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
        self.effects = [Effect(effect_data) for effect_data in data["effects"]]


class Effect:
    """效果类"""

    def __init__(self, data: Dict):
        self.type = EffectType(data["type"])
        self.params = data.get("params", {})
