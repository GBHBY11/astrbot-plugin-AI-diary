# AI bot diary

[English](README.md) | [简体中文](README.zh-CN.md)

[下载 ZIP](https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip) · [GitHub 仓库](https://github.com/GBHBY11/astrbot-plugin-AI-diary)

给 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的私密日记记忆插件。Bot 会记录当天的聊天，按人设写一篇短日记；回复时最多召回两篇最近日记。日记不会被原文背诵，Bot 也不会说“我写了日记”。

## 功能

- 按会话隔离：每个群、每个私聊各自一篇，不串味
- 每天定时写一篇，默认 `23:30`
- 回复时召回最近 1~2 篇，注入 system prompt
- 手机号、身份证、密码脱敏
- 生成或发送失败时静默跳过，不把异常发进群
- 管理员命令 `/写日记` 可立即生成当前会话今天的日记
- 纯标准库，不需要额外 pip 依赖

## 环境要求

- AstrBot 4.x
- 已配置可用的聊天模型
- 一份人格提示词。仓库自带的 `persona.txt` 是示例，可以用它，也可以换成你自己的

## 快速安装

### 方式一：下载 ZIP

1. 点击 **[下载 ZIP](https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip)**
2. 解压后会得到 `astrbot-plugin-AI-diary-main` 文件夹
3. 把文件夹重命名为：

```text
astrbot_plugin_ai_diary
```

4. 放进 AstrBot 的插件目录：

```text
AstrBot/data/plugins/astrbot_plugin_ai_diary/
```

如果 AstrBot 跑在 Docker 里，放到宿主机挂载到 `/AstrBot/data/plugins` 的目录；容器内路径是 `/AstrBot/data/plugins/astrbot_plugin_ai_diary`。

5. 重启 AstrBot，或在 WebUI 里重载插件

最终目录必须是：

```text
astrbot_plugin_ai_diary/
├── main.py
├── ai_diary.py
├── metadata.yaml
├── _conf_schema.json
├── persona.txt
├── README.md
├── README.zh-CN.md
├── CHANGELOG.md
└── LICENSE
```

### 方式二：git clone

```bash
cd AstrBot/data/plugins
git clone https://github.com/GBHBY11/astrbot-plugin-AI-diary.git astrbot_plugin_ai_diary
```

然后重启 AstrBot。

## 配置人格

插件不会自动创建人格。

1. 打开 AstrBot WebUI → **人格**
2. 新建人格，名称填 `AI bot diary`
3. 打开仓库里的 `persona.txt`，把内容粘贴为 system prompt；也可以换成人格
4. 把这个人格绑定到需要使用日记的 Agent / 会话
5. 保留日记规则：私密记忆、不背原文、不说“我写了日记”

如果你用自己的角色，记得在提示词里写清楚：日记是私密记忆，不能对外暴露。

## 配置插件

打开 **AstrBot → 插件 → AI bot diary → 配置**。

| 配置 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 启用日记 |
| `write_hour` | `23` | 写日记小时 |
| `write_minute` | `30` | 写日记分钟 |
| `diary_min_chars` | `60` | 日记最少字数 |
| `diary_max_chars` | `150` | 日记最多字数 |
| `provider_id` | 空 | 写日记模型；空=默认模型 |
| `recall_limit` | `2` | 每次最多召回几篇 |
| `max_transcript_chars` | `6000` | 写日记读取的最大聊天字符数 |

`diary_max_chars` 超过 300 时，存储硬上限会自动放宽。

## 命令

```text
/写日记
```

立即生成当前会话今天的日记，仅管理员可用。

## 数据位置

```text
data/plugin_data/astrbot_plugin_ai_diary/
├── diary/<会话>/<YYYY-MM>.jsonl
└── transcripts/<会话>/<YYYY-MM-DD>.jsonl
```

会话名为 `group_<群号>` 或 `private_<QQ号>`。

## 从旧插件 ID 升级

这个版本把插件 ID 从 `astrbot_plugin_dafeiyu_diary` 改成了 `astrbot_plugin_ai_diary`。

安装前先停用或删除旧插件目录，然后重命名数据目录，保留已有日记：

```bash
cd AstrBot/data/plugin_data
mv astrbot_plugin_dafeiyu_diary astrbot_plugin_ai_diary
```

Windows PowerShell：

```powershell
Rename-Item "AstrBot\data\plugin_data\astrbot_plugin_dafeiyu_diary" "astrbot_plugin_ai_diary"
```

然后按新目录 `astrbot_plugin_ai_diary` 安装并重启 AstrBot。不要同时运行两个插件 ID。

## 工作原理

1. 收到的文本消息写入当前会话当天的聊天记录
2. 到 `write_hour:write_minute`，插件把聊天记录和人格提示词发给配置的模型
3. 生成的日记脱敏后写入 JSONL
4. 下一次 LLM 请求时，插件召回最多 `recall_limit` 篇，拼进 system prompt
5. 人设把日记当作私密记忆：不背原文、不说“我写了日记”

## 项目命名

仓库名和 AstrBot 插件 ID 是分开的：

- GitHub 仓库：`astrbot-plugin-AI-diary`
- AstrBot 插件 ID：`astrbot_plugin_ai_diary`
- 显示名称：`AI bot diary`

AstrBot 要求 `metadata.yaml` 的 `name` 是合法 Python 模块名，不能带连字符。所以 `astrbot-plugin-AI-diary` 只能作为项目名，实际加载使用下划线版本。

## 常见问题

- **插件列表里没有**：确认目录名是 `astrbot_plugin_ai_diary`，且 `metadata.yaml` 在根目录
- **不写日记**：检查模型是否可用，以及当天聊天素材是否足够
- **`/写日记` 提示没权限**：这个命令仅管理员可用
- **没有召回**：至少要先写过一篇日记，且 `recall_limit` 大于 0
- **旧日记不见了**：按“从旧插件 ID 升级”重命名数据目录

## 说明

- 只记录文本消息，图片不会写入
- 当天素材不足时不硬写空日记
- 日记是本地 JSONL，请像其他 AstrBot 数据一样备份

## 许可

MIT License，见 [LICENSE](LICENSE)。

允许使用、复制、修改、分发、再许可和商业使用，只需保留版权声明和许可声明。

仓库自带人格文本是示例；如果你替换或再分发角色设定，请保留原作者署名，并确认你有权分享相关角色素材。
