# 真寻农场预览版

本文件随生成包分发；业务源码只在主仓库main_plugin_farm维护。
生成目标为Shu-Ying/zhenxun_plugin_farm的farm-preview分支，保留main。

preview.3恢复旧版信息底板和头像框、昵称、经验进度、等级及两种货币。
按用户确认校正原素材上的字段错位，保留旧版经验计算口径；点券显示
真实余额。仍使用目标尺寸绘制、一次快照查询及有界缓存。

## 安装前

此版沿用“开通农场”“我的农场”等原指令，没有测试前缀。请先停止
机器人，并停用旧农场插件，避免同名指令被旧版抢先处理。仅在菜单
禁用旧版不一定阻止其导入；建议把旧插件目录备份到插件扫描目录之外。
安装脚本不会自动禁用、删除或覆盖旧版。

预览数据默认位于真寻DATA_PATH/farm_preview/farm-preview.sqlite3。
不读取旧版数据库，不迁移真实玩家资产；同平台、同机器人内共享农场，
不同机器人/平台分开。不要将预览数据路径指向旧版数据库。

## 主仓库本地生成

```text
python scripts/build_zhenxun.py --output dist/zhenxun-preview
python scripts/verify_zhenxun.py dist/zhenxun-preview/zhenxun_plugin_farm_preview-0.1.0-preview.1.zip
python scripts/install_zhenxun.py dist/zhenxun-preview/zhenxun_plugin_farm_preview-0.1.0-preview.1.zip --plugins-dir /path/to/zhenxun_bot/zhenxun/plugins
```

必须使用真寻的Python环境安装包内requirements.txt；该依赖约束为
Pillow>=10.4,<11，不静默升级宿主到12。NoneBot、真寻和Uninfo由
现有宿主提供，不把通用NoneBot适配器或AstrBot代码一起分发。

如果安装目录已存在，脚本会拒绝覆盖。更新前停机器人、备份插件目录，
手动移走旧预览目录后再安装；数据目录位于插件外，不随插件删除。

## 配置与指令

默认优先使用真寻FONT_PATH目录下已有的中文字体，依次尝试
HYWenHei-85W.ttf、msyh.ttf、syht.otf、syst.otf、
AlibabaHealthFont2.0CN-85B.ttf；文件损坏会继续尝试下一个。
宿主目录均不可用时，再尝试Windows微软雅黑/宋体或Linux常用
Noto Sans CJK/文泉驿路径。不会下载或打包额外字体。

上述默认路径仅属于真寻适配层，不作为其他机器人宿主的默认配置。
NoneBot/AstrBot接入时分别解析各自字体资源；共享farm_render只接收
最终文件路径，不依赖真寻FONT_PATH或固定resources/font目录。

通常不必额外配置；需要覆盖默认字体时，在真寻使用的.env指定路径：

```dotenv
FARM_PREVIEW_FONT=C:/Windows/Fonts/msyh.ttc
FARM_PREVIEW_DEPLOYMENT=zhenxun-preview
FARM_PREVIEW_IMAGE_FORMAT=AUTO
```

Linux请提供合法可用的中文字体。显式配置优先，配置错误时不会静默
替换成其他字体。所有默认候选都不可用时，文本交易可用，图片命令
会提示配置；不捆绑Windows字体。可选FARM_PREVIEW_DATA_DIR显式设置
独立预览数据目录。AUTO默认JPEG以保守兼容真实平台，确认WebP支持后
可设WEBP，也支持JPEG/PNG。

测试顺序（是否需要/前缀遵循宿主COMMAND_START配置）：

```text
农场帮助
开通农场
我的农场
种子商店
购买种子 白萝卜 1
我的种子
播种 白萝卜 1
我的农场 高清
农场详述
收获
```

作物未成熟时收获会明确失败，不提供管理员快进命令或加币后门。
其他入口：铲除、我的作物、我的农场币、我的点券、作物加锁 作物、
作物解锁 作物、出售作物 作物 数量；不带参数出售全部未锁定产物。
也可发送“我的农场 buy-seed 白萝卜 1”等旧子命令（支持范围见帮助）。
不实现签到、偷菜、充值、兑换、升级和旧数据迁移，不能替代旧版全部功能。

重复事件通过稳定消息标识幂等；无法获取消息标识时写操作拒绝。
头像最多等待2秒，失败使用默认图；图片缓存与后台任务均有限额。
关键日志写入数据目录farm-preview.log，同时沿用宿主日志传播配置；
不记录真实玩家数据。

## GitHub工作流

先由你提交主仓库代码后，主仓库的Zhenxun preview工作流会检查并上传
Actions artifact。下载并解压附件，取其中插件ZIP安装；不需要令牌。
Windows/Linux、Pillow10.4/当前支持版属于CI矩阵，不代表本机已跑Linux。

若还需将生成内容写入发布仓库，主仓库手动Run workflow时勾选publish，
并配置受保护environment zhenxun-preview。该环境Secret名为
FARM_RELEASE_TOKEN，仅授权目标仓库Contents写入；生成内容含工作流，
相应令牌也须允许Workflows写入（GitHub App使用对应权限）。配置
环境审批及仅允许main分支部署。不把Token填进脚本、URL或输入参数。
脚本默认dry-run，只有--publish才访问GitHub；固定写farm-preview，
不更新main、不force、不创建Release。第一次创建预览分支，之后普通
提交更新。专用预览分支只放生成内容，不在那里手改业务或存储治理资料。
已有预览分支必须带本项目来源清单；若它已成为默认分支则拒绝发布，
并发期间分支发生变化也拒绝更新，避免覆盖其他提交。
用ZIP安装最直接，不能假设插件管理器支持任意分支地址。

产物内FARM-MANIFEST.json记录版本、源提交、dirty和每文件SHA256；
源有未提交修改会标dirty，禁止发布这种产物。本地测试允许dirty。
哈希用于内容一致性，不是签名或来源身份保证，请使用你信任的附件。

## 验证边界与回退

本轮不会在真实机器人中安装/启动，也不会执行真实GitHub同步。真实
登录、权限、适配器消息格式和发图需要你部署后验证，不能把离线模拟
报告为线上成功。旧素材455个阶段引用缺图时显示问号，不会整图失败。

源码中ZIP时间、系统类型和文件权限固定；文本统一LF，以便跨平台
复现。构建后repository目录是发布仓库根，外层插件ZIP用于本地安装；
二者不要再叠套一层主仓库目录。

回退：停机器人，移走预览插件，恢复旧插件目录，再由你启动；旧版库
没有被本版更改。保留预览数据备份，不尝试让旧版打开新SQLite schema。

官方依据：[Actions附件](https://docs.github.com/en/actions/tutorials/store-and-share-data)、
[手动触发](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)。
