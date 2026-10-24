<h1 align="center">📔 AI bot diary</h1>

<p align="center">
  <strong>AstrBot 的私密日记记忆插件</strong><br>
  记录当天聊天，按人设写一篇短日记，回复时自然回忆。
</p>

<p align="center">
  <a href="https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip">
    <img src="https://img.shields.io/badge/下载-ZIP-2ea44f?style=for-the-badge" alt="下载 ZIP">
  </a>
  <a href="https://github.com/AstrBotDevs/AstrBot">
    <img src="https://img.shields.io/badge/AstrBot-4.x-6f42c1?style=flat-square" alt="AstrBot 4.x">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="MIT License">
</p>

<p align="center">
  <img src="assets/hero.jpg" width="240" alt="AI bot diary 鲸鱼娘表情包">
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="https://github.com/GBHBY11/astrbot-plugin-AI-diary">GitHub</a> · <a href="https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip">下载 ZIP</a>
</p>

给 AstrBot 的私密日记记忆插件。Bot 会记录当天的聊天，按人设写一篇短日记；回复时最多召回两篇最近日记。日记不会被原文背诵，Bot 也不会说“我写了日记”。

## ✨ 功能

- 🗂️ **按会话隔离** —— 每个群、每个私聊各自一篇，不串味
- 🌙 **每天定时写** —— 默认 `23:30`，每个活跃会话每天一篇
- 🧠 **自然召回** —— 回复时最多召回两篇，注入 system prompt
- 🔒 **隐私脱敏** —— 手机号、身份证、密码写入前替换
- 🤫 **静默失败** —— 生成或发送失败不把异常发进群
- ⌨️ **手动命令** —— 管理员可执行 `/写日记` 立即生成
- 📦 **纯标准库** —— 不需要额外 pip 依赖

<p align="center">
  <img src="assets/sticker.jpg" width="160" alt="AI bot diary 开心表情包">
</p>

## 🚀 快速安装

### 方式一：下载 ZIP

1. 点击 **[下载 ZIP](https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip)**
2. 解压后会得到 `astrbot-plugin-AI-diary-main`
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
├── assets/
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

## 🧠 配置人格

插件不会自动创建人格。

1. 打开 AstrBot WebUI → **人格**
2. 新建人格，名称填 `AI bot diary`
3. 打开仓库里的 `persona.txt`，把内容粘贴为 system prompt；也可以换成人格
4. 把这个人格绑定到需要使用日记的 Agent / 会话
5. 保留日记规则：私密记忆、不背原文、不说“我写了日记”

如果你用自己的角色，记得在提示词里写清楚：日记是私密记忆，不能对外暴露。

## ⚙️ 配置插件

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

## 💬 命令

```text
/写日记
```

立即生成当前会话今天的日记，仅管理员可用。

## 🗂️ 数据位置

```text
data/plugin_data/astrbot_plugin_ai_diary/
├── diary/<会话>/<YYYY-MM>.jsonl
└── transcripts/<会话>/<YYYY-MM-DD>.jsonl
```

会话名为 `group_<群号>` 或 `private_<QQ号>`。

## 🔄 从旧插件 ID 升级

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

## 🧩 工作原理

1. 收到的文本消息写入当前会话当天的聊天记录
2. 到 `write_hour:write_minute`，插件把聊天记录和人格提示词发给配置的模型
3. 生成的日记脱敏后写入 JSONL
4. 下一次 LLM 请求时，插件召回最多 `recall_limit` 篇，拼进 system prompt
5. 人设把日记当作私密记忆：不背原文、不说“我写了日记”

## 🏷️ 项目命名

仓库名和 AstrBot 插件 ID 是分开的：

- GitHub 仓库：`astrbot-plugin-AI-diary`
- AstrBot 插件 ID：`astrbot_plugin_ai_diary`
- 显示名称：`AI bot diary`

AstrBot 要求 `metadata.yaml` 的 `name` 是合法 Python 模块名，不能带连字符。所以 `astrbot-plugin-AI-diary` 只能作为项目名，实际加载使用下划线版本。

## 🛠️ 常见问题

- **插件列表里没有** —— 确认目录名是 `astrbot_plugin_ai_diary`，且 `metadata.yaml` 在根目录
- **不写日记** —— 检查模型是否可用，以及当天聊天素材是否足够
- **`/写日记` 提示没权限** —— 这个命令仅管理员可用
- **没有召回** —— 至少要先写过一篇日记，且 `recall_limit` 大于 0
- **旧日记不见了** —— 按“从旧插件 ID 升级”重命名数据目录

## 📝 说明

- 只记录文本消息，图片不会写入
- 当天素材不足时不硬写空日记
- 日记是本地 JSONL，请像其他 AstrBot 数据一样备份

## 📜 许可

MIT License，见 [LICENSE](LICENSE)。

允许使用、复制、修改、分发、再许可和商业使用，只需保留版权声明和许可声明。

仓库自带人格文本是示例；如果你替换或再分发角色设定，请保留原作者署名，并确认你有权分享相关角色素材。
