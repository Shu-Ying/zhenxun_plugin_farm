<div align="center">

# 真寻农场(zhenxun_plugin_farm)
<p align="center">
    <a href="./LICENSE">
        <img src="https://img.shields.io/badge/license-GPL3.0-FE7D37" alt="license">
    </a>
    <a href="https://www.python.org">
        <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python">
    </a>
    <a href="https://nonebot.dev/">
        <img src="https://img.shields.io/badge/Nonebot-2.0.0%2B-black" alt="Nonebot">
    </a>
    <a href="https://github.com/zhenxun-org/zhenxun_bot">
        <img src="https://img.shields.io/badge/zhenxun-0.2.4%2B-%23ECD9D3" alt="Python">
    </a>
</p>

<p align="center">

[![tencent-qq](https://img.shields.io/badge/%E7%BE%A4-%E7%9C%9F%E5%AF%BB%E5%86%9C%E5%9C%BA%E6%B5%8B%E8%AF%95-%23FF99CC
)](https://qm.qq.com/q/7hsOD4rOw2)

</p>

你是说可以种地对吧🤔?

</div>

---
## 目录
- [真寻农场(zhenxun\_plugin\_farm)](#真寻农场zhenxun_plugin_farm)
  - [目录](#目录)
  - [农场界面](#农场界面)
  - [如何安装](#如何安装)
  - [使用指令](#使用指令)
  - [更新日志(详细)：](#更新日志详细)
  - [用户方面](#用户方面)
  - [代码方面](#代码方面)
  - [待办事宜 `Todo` 列表](#待办事宜-todo-列表)
  - [关于](#关于)
  - [致谢](#致谢)
  - [许可证](#许可证)

---

## 农场界面

![农场界面](./resource/1.png)

---

## 如何安装

方法一（推荐）：在小真寻后台的插件商店下载即可<br>
方法二：下载源码放在小真寻`plugin`目录下

---

## 使用指令

| 指令 | 描述 | Tip |
| --- | --- | --- |
| @小真寻 开通农场 | 首次开通农场 |  |
| 我的农场 | 你的农场 |  |
| 农场详述 | 农场详细信息 |  |
| 我的农场币 | 查询农场币 |  |
| 种子商店 [筛选关键字] [页数] or [页数] | 查看种子商店 | 当第一个参数为非整数时，会默认进入筛选状态。页数不填默认为1 |
| 购买种子 [种子名称] [数量] | 购买种子 | 数量不填默认为1 |
| 我的种子 | 查询仓库种子 |  |
| 播种 [种子名称] [数量] | 播种种子 | 数量不填默认将最大可能播种 |
| 收获 | 收获成熟作物 |  |
| 铲除 | 铲除荒废作物 |  |
| 我的作物 | 你的作物 |  |
| 出售作物 [作物名称] [数量] | 从仓库里向系统售卖作物 | 不填写作物名将售卖仓库种全部作物 填作物名不填数量将指定作物全部出售 |
| 偷菜 @美波理 | 偷别人的菜 | 每人每天只能偷5次 |
| 购买农场币 | 将真寻金币兑换成农场币 | 兑换比例默认为1:2 手续费默认20% |
| 更改农场名 [新的农场名] | 改名 | 农场名称无法存储特殊字符 |
| 农场签到 | 签到 | 需要注意，该项会从服务器拉取签到数据 |
| 土地升级 [地块ID] | 将土地升级，带来收益提升 | 如果土地升级时，土地有播种作物，那么将直接成熟 |

---

## 更新日志[(详细)](./log/log.md)：
用户方面
---
- 新增土地升级指令，快来将土地升级至红土地、黑土地、金土地吧
- 新增查漏补缺作物资源功能，自动更新最新作物和作物资源文件
- 定时更新签到文件、作物资源从00:30调整至04:30
- 修正了部分土地资源错误的情况
- 修正了部分文本信息错误的情况

代码方面
---
- 修正部分事件连接机制
- 修正网络请求端口

## 待办事宜 `Todo` 列表

- [x] 完善我的农场图片，例如左上角显示用户数据
- [ ] 完善升级数据、作物数据、作物图片
- [x] 签到功能
- [x] 在线更新作物信息
- [ ] 添加渔场功能
- [ ] 增加活动、交易行功能
- [ ] 增加交易行总行功能
- [ ] 添加其他游戏种子素材
- [ ] 想不到了，想到再说

---

## 关于

本人毫无任何Python经验，也从未正式的、系统的、完整的去学习Python。如有看到写的不对的地方，欢迎指出，也欢迎任何人一起来开发、完善农场。

素材来均源于互联网，侵权请联系我删除

---

## 致谢

最后感谢以下框架/作者的提供的技术支持(排名不分先后):

- [Nonebot2](https://github.com/nonebot/nonebot2) *✨ 跨平台 Python 异步机器人框架 ✨*
- [zhenxun_bot](https://github.com/zhenxun-org/zhenxun_bot) *最爱真寻的一集*
- [HibiKier](https://github.com/HibiKier) *阿咪为什么是神*
- [ATTomato](https://github.com/ATTomatoo) *流泪偷码头.jpg*

## 许可证

`真寻农场(zhenxun_plugin_farm)`将采用的是`GPLv3`许可证进行开源
