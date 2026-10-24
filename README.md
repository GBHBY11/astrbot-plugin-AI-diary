<h1 align="center">📔 AI bot diary</h1>

<p align="center">
  <strong>A private daily-diary memory plugin for AstrBot.</strong><br>
  Your bot records the day, writes a short diary in character, and remembers it naturally.
</p>

<p align="center">
  <a href="https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip">
    <img src="https://img.shields.io/badge/Download-ZIP-2ea44f?style=for-the-badge" alt="Download ZIP">
  </a>
  <a href="https://github.com/AstrBotDevs/AstrBot">
    <img src="https://img.shields.io/badge/AstrBot-4.x-6f42c1?style=flat-square" alt="AstrBot 4.x">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="MIT License">
</p>

<p align="center">
  <img src="assets/hero.jpg" width="240" alt="AI bot diary mascot holding out a hand">
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a> · <a href="https://github.com/GBHBY11/astrbot-plugin-AI-diary">GitHub</a> · <a href="https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip">Download ZIP</a>
</p>

AstrBot plugin that gives your bot a private diary. It records the day's chat, writes one short entry in character, and recalls up to two recent entries when it replies. The diary is never quoted verbatim, and the bot is instructed never to mention that it keeps one.

## ✨ Features

- 🗂️ **Per-session isolation** — every group and private chat has its own diary.
- 🌙 **Daily writing** — one entry per active session per day.
- 🧠 **Natural recall** — up to two recent entries are injected into the system prompt.
- 🔒 **Privacy scrub** — phone numbers, ID numbers and passwords are replaced before storage.
- 🤫 **Fail silently** — generation and delivery errors never leak into chat.
- ⌨️ **Manual command** — an admin can run `/写日记` immediately.
- 📦 **Pure standard library** — no extra Python packages.

<p align="center">
  <img src="assets/sticker.jpg" width="160" alt="Happy AI bot diary mascot sticker">
</p>

## 🚀 Quick install

### Option 1: download ZIP

1. Click the **[Download ZIP](https://github.com/GBHBY11/astrbot-plugin-AI-diary/archive/refs/heads/main.zip)** button.
2. Extract it. You will get `astrbot-plugin-AI-diary-main`.
3. Rename that folder to:

```text
astrbot_plugin_ai_diary
```

4. Put it into AstrBot's plugin directory:

```text
AstrBot/data/plugins/astrbot_plugin_ai_diary/
```

Docker: use the host directory mounted to `/AstrBot/data/plugins`; inside the container the path is `/AstrBot/data/plugins/astrbot_plugin_ai_diary`.

5. Restart AstrBot, or reload the plugin from the WebUI.

The final layout must be:

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

### Option 2: git clone

```bash
cd AstrBot/data/plugins
git clone https://github.com/GBHBY11/astrbot-plugin-AI-diary.git astrbot_plugin_ai_diary
```

Restart AstrBot afterwards.

## 🧠 Configure the persona

The plugin does not create a persona automatically.

1. Open AstrBot WebUI → **Personas**.
2. Create a new persona named `AI bot diary`.
3. Paste `persona.txt` from this repository as the system prompt, or use your own persona.
4. Bind that persona to the agent/session that should use the diary.
5. Keep the diary rules: private memory, no verbatim quotes, never say "I wrote a diary".

If you use your own persona, add the diary rules to it so the bot treats the diary as private memory.

## ⚙️ Configure the plugin

Open **AstrBot → Plugins → AI bot diary → Config**.

| Key | Default | Description |
|---|---|---|
| `enabled` | `true` | Enable the diary |
| `write_hour` | `23` | Hour of the daily diary job |
| `write_minute` | `30` | Minute of the daily diary job |
| `diary_min_chars` | `60` | Minimum diary length |
| `diary_max_chars` | `150` | Maximum diary length |
| `provider_id` | empty | Provider used for diary writing; empty = default |
| `recall_limit` | `2` | Number of diary entries recalled per reply |
| `max_transcript_chars` | `6000` | Maximum chat transcript characters sent to the model |

The hard storage limit is automatically raised when `diary_max_chars` is greater than 300.

## 💬 Commands

```text
/写日记
```

Writes the current session's diary immediately. Only AstrBot admins can use it.

## 🗂️ Data layout

```text
data/plugin_data/astrbot_plugin_ai_diary/
├── diary/<session>/<YYYY-MM>.jsonl
└── transcripts/<session>/<YYYY-MM-DD>.jsonl
```

`<session>` is `group_<id>` or `private_<user_id>`, so groups and private chats never share diaries.

## 🔄 Upgrading from the old plugin ID

This release changes the AstrBot plugin ID from `astrbot_plugin_dafeiyu_diary` to `astrbot_plugin_ai_diary`.

Disable or remove the old plugin folder, then rename the data directory so existing diaries are kept:

```bash
cd AstrBot/data/plugin_data
mv astrbot_plugin_dafeiyu_diary astrbot_plugin_ai_diary
```

Windows PowerShell:

```powershell
Rename-Item "AstrBot\data\plugin_data\astrbot_plugin_dafeiyu_diary" "astrbot_plugin_ai_diary"
```

Then install this version as `astrbot_plugin_ai_diary` and restart AstrBot. Do not run both plugin IDs at the same time.

## 🧩 How it works

1. Incoming text messages are written to the session's daily transcript.
2. At `write_hour:write_minute`, the plugin sends the transcript and persona prompt to the configured provider.
3. The generated entry is scrubbed and stored as JSONL.
4. On the next LLM request, the plugin retrieves up to `recall_limit` entries and appends a recall block to the system prompt.
5. The persona treats the diary as private memory: never quote it, never say "I wrote a diary".

## 🏷️ Project naming

The repository name and AstrBot plugin ID are intentionally different:

- GitHub repository: `astrbot-plugin-AI-diary`
- AstrBot plugin ID: `astrbot_plugin_ai_diary`
- Display name: `AI bot diary`

AstrBot requires `metadata.yaml`'s `name` to be a valid Python module identifier. Hyphens are not allowed, so `astrbot-plugin-AI-diary` cannot be used as the plugin ID. The hyphenated name is kept for the GitHub project; the underscored ID is what AstrBot loads.

## 🛠️ Troubleshooting

- **Plugin does not appear** — confirm the folder is named `astrbot_plugin_ai_diary` and `metadata.yaml` is at its root.
- **No diary is written** — check that the provider works and the day's transcript has enough text.
- **`/写日记` says no permission** — the command is admin-only.
- **No recall** — at least one diary must exist, and `recall_limit` must be greater than 0.
- **Old diaries missing** — follow the data-directory rename in "Upgrading from the old plugin ID".

## 📝 Notes

- Images and other non-text messages are not written to the transcript.
- If there is not enough chat material, the plugin skips the day instead of inventing an entry.
- The diary is local JSONL; back it up like any other AstrBot data.

## 📜 License

MIT License. See [LICENSE](LICENSE).

You may use, copy, modify, distribute, sublicense, and sell copies of this project, provided that the copyright notice and permission notice are included.

The bundled persona text is a sample. If you replace or redistribute it, keep the original attribution and make sure you have the right to share the character material.
