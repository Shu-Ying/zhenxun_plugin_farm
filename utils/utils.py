from enum import Enum


class Festival(Enum):
    NO = 0  # 无节日
    MIDAUTUMN = 1  # 中秋节
    NATIONALDAY = 2  # 国庆节
    LANTERNFESTIVAL = 3  # 元宵节
    DRAGONBOAT = 4  # 端午节
    SPRINGFESTIVAL = 5  # 春节
    HALLOWEEN = 6  # 万圣节
    CHRISTMAS = 7  # 圣诞节
    NEWYEAR = 8  # 新年
    VALENTINE = 9  # 情人节


class Season(Enum):
    NO = 0  # 无季节
    SPRING = 1  # 春季
    SUMMER = 2  # 夏季
    AUTUMN = 3  # 秋季
    WINTER = 4  # 冬季
