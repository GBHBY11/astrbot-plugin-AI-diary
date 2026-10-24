# Dafeiyu Diary

A lightweight diary-memory plugin for [AstrBot](https://github.com/AstrBotDevs/AstrBot), built for the **Dafeiyu / 大肥鱼** persona.

The bot records the day's chat, writes one short private diary entry in character, and recalls up to two recent entries when it replies. The diary is never quoted verbatim and the bot is instructed never to mention that it keeps a diary.

## Features

- Per-session isolation: every group and private chat has its own diary.
- Daily writing: one entry per active session per day.
- Recall: up to two recent entries are injected into the system prompt.
- Privacy scrub: phone numbers, ID numbers and passwords are replaced before storage.
- Fail silently: generation and delivery errors never leak into the chat.
- Manual command: an admin can run `/写日记` to write the current session's entry immediately.
- Pure standard library: no extra Python packages.

## Requirements

- AstrBot 4.x
- A working chat provider configured in AstrBot
- A persona that matches the supplied `persona.txt`, or your own persona

## Installation

### Option 1: copy the folder

Copy this repository into AstrBot's plugin directory and rename the folder to the plugin ID:

```text
AstrBot/data/plugins/astrbot_plugin_dafeiyu_diary/
```

The final layout should look like:

```text
astrbot_plugin_dafeiyu_diary/
├── main.py
├── dafeiyu_diary.py
├── metadata.yaml
├── _conf_schema.json
├── persona.txt
└── README.md
```

Restart AstrBot or reload the plugin from the WebUI.

### Option 2: install from GitHub

After publishing the repository, install it from AstrBot's plugin market using the GitHub URL, or clone it into `data/plugins/astrbot_plugin_dafeiyu_diary`.

## Configuration

Open **AstrBot → Plugins → Dafeiyu Diary → Config**.

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

## Commands

```text
/写日记
```

Writes the current session's diary immediately. Only AstrBot admins can use it.

## Data layout

```text
data/plugin_data/astrbot_plugin_dafeiyu_diary/
├── diary/<session>/<YYYY-MM>.jsonl
└── transcripts/<session>/<YYYY-MM-DD>.jsonl
```

`<session>` is `group_<id>` or `private_<user_id>`, so groups and private chats never share diaries.

## How it works

1. Incoming text messages are written to the session's daily transcript.
2. At `write_hour:write_minute`, the plugin sends the transcript and the persona prompt to the configured provider.
3. The generated entry is scrubbed and stored as JSONL.
4. On the next LLM request, the plugin retrieves up to `recall_limit` entries and appends a recall block to the system prompt.
5. The persona is told to treat the diary as private memory: never quote it, never say "I wrote a diary".

## Customization

`persona.txt` contains the Dafeiyu persona prompt. You can replace it with your own character, but keep the diary rules if you want the same behavior.

The project name and plugin ID are intentionally separate:

- GitHub repository: `astrbot-plugin-AI-diary`
- AstrBot plugin ID: `astrbot_plugin_dafeiyu_diary`

## Notes

- Images and other non-text messages are not written to the transcript.
- If there is not enough chat material, the plugin skips the day instead of inventing an entry.
- The diary is local JSONL; back it up like any other AstrBot data.

## License

MIT License. See [LICENSE](LICENSE).

You may use, copy, modify, distribute, sublicense, and sell copies of this
project, provided that the copyright notice and permission notice are included.

The Dafeiyu persona text is included as part of this project. If you replace or
redistribute it, keep the original attribution and make sure you have the right
to share the character material.
