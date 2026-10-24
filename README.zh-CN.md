# 大肥鱼日记 / Dafeiyu Diary

给 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的「大肥鱼」人格加一个会自己写日记的轻量插件。

Bot 会把当天的群聊/私聊记录下来，每天写一篇符合人设的短日记；回复时最多召回两篇最近日记，但不会背原文，也不会说“我写了日记”。

## 功能

- 按会话隔离：每个群、每个私聊各自一篇，不串味
- 每天定时写一篇，默认 `23:30`
- 回复时召回最近 1~2 篇，注入 system prompt
- 手机号、身份证、密码脱敏
- 生成或发送失败时静默跳过，不把异常发进群
- 管理员命令 `/写日记` 可立即生成当前会话今天的日记
- 纯标准库，不需要额外 pip 依赖

## 环境

- AstrBot 4.x
- 已配置可用的聊天模型
- 已配置对应人格（可使用本仓库的 `persona.txt`）

## 安装

把仓库放到 AstrBot 插件目录，并重命名为插件 ID：

```text
AstrBot/data/plugins/astrbot_plugin_dafeiyu_diary/
```

最终结构：

```text
astrbot_plugin_dafeiyu_diary/
├── main.py
├── dafeiyu_diary.py
├── metadata.yaml
├── _conf_schema.json
├── persona.txt
└── README.md
```

重启 AstrBot，或在 WebUI 中重载插件。

## 配置

AstrBot → 插件 → Dafeiyu Diary → 配置：

| 配置 | 默认 | 说明 |
|---|---|---|
| `enabled` | true | 启用日记 |
| `write_hour` | 23 | 写日记小时 |
| `write_minute` | 30 | 写日记分钟 |
| `diary_min_chars` | 60 | 日记最少字数 |
| `diary_max_chars` | 150 | 日记最多字数 |
| `provider_id` | 空 | 写日记模型；空=默认模型 |
| `recall_limit` | 2 | 每次最多召回几篇 |
| `max_transcript_chars` | 6000 | 写日记读取的最大聊天字符数 |

`diary_max_chars` 超过 300 时，存储硬上限会自动放宽。

## 命令

```text
/写日记
```

立即生成当前会话今天的日记，仅管理员可用。

## 数据位置

```text
data/plugin_data/astrbot_plugin_dafeiyu_diary/
├── diary/<会话>/<YYYY-MM>.jsonl
└── transcripts/<会话>/<YYYY-MM-DD>.jsonl
```

会话名为 `group_<群号>` 或 `private_<QQ号>`。

## 说明

- 只记录文本消息，图片不会写入
- 当天素材不足时不硬写空日记
- 日记是本地 JSONL，请像其他 AstrBot 数据一样备份

## 项目命名

- GitHub 仓库：`astrbot-plugin-AI-diary`
- AstrBot 插件 ID：`astrbot_plugin_dafeiyu_diary`

## 许可

MIT License，见 [LICENSE](LICENSE)。

允许使用、复制、修改、分发、再许可和商业使用，只需保留版权声明和许可声明。

人格文本随项目一起提供；如果你替换或再分发角色设定，请保留原作者署名，并确认你有权分享相关角色素材。
