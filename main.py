"""AstrBot plugin: a private daily-diary memory for your bot.

依赖同目录的 ai_diary.py（标准库实现）。
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.core.star.star_tools import StarTools

from . import ai_diary as diary_module
from .ai_diary import DiaryStore, build_recall_block, build_write_messages


@register(
    "astrbot_plugin_ai_diary",
    "DSH",
    "A private daily-diary memory plugin for AstrBot.",
    "1.1.0",
    "https://github.com/GBHBY11/astrbot-plugin-AI-diary",
)
class AiBotDiaryPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self.data_dir = Path(StarTools.get_data_dir("astrbot_plugin_ai_diary"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store = DiaryStore(str(self.data_dir / "diary"))
        self.transcript_root = self.data_dir / "transcripts"
        self.transcript_root.mkdir(parents=True, exist_ok=True)
        self.persona = self._read_persona()
        self._last_written_day = ""
        self._seen: set[str] = set()
        self._task = asyncio.create_task(self._diary_loop())
        logger.info("[AI bot diary] 已加载，数据目录=%s", self.data_dir)

    def _cfg(self, key, default):
        try:
            return self.config.get(key, default)
        except Exception:
            return default

    def _length_range(self):
        try:
            minimum = int(self._cfg("diary_min_chars", 60))
        except Exception:
            minimum = 60
        try:
            maximum = int(self._cfg("diary_max_chars", 150))
        except Exception:
            maximum = 150
        minimum = max(20, min(1000, minimum))
        maximum = max(minimum + 10, min(2000, maximum))
        return minimum, maximum

    def _read_persona(self):
        path = Path(__file__).with_name("persona.txt")
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return "你是一个有自己生活的角色。"

    @staticmethod
    def _safe(value: str) -> str:
        return re.sub(r"[^\w\-]", "_", str(value or "unknown"))

    def _session_key(self, event: AstrMessageEvent) -> str:
        try:
            if event.is_private_chat():
                return "private_" + str(event.get_sender_id() or "unknown")
            group_id = event.get_group_id()
            if group_id:
                return "group_" + str(group_id)
            return str(event.unified_msg_origin or "unknown")
        except Exception:
            return str(getattr(event, "unified_msg_origin", "unknown"))

    def _provider(self, event: AstrMessageEvent | None = None):
        provider_id = str(self._cfg("provider_id", "") or "").strip()
        if provider_id:
            try:
                provider = self.context.get_provider_by_id(provider_id)
                if provider:
                    return provider
            except Exception:
                pass
        try:
            if event is not None:
                return self.context.get_using_provider(event.unified_msg_origin)
            return self.context.get_using_provider()
        except Exception:
            return None

    def _record(self, session: str, role: str, name: str, text: str, message_id: str = ""):
        text = (text or "").strip()
        if not text:
            return
        key = f"{session}|{role}|{message_id or text[:80]}"
        if key in self._seen:
            return
        self._seen.add(key)
        if len(self._seen) > 3000:
            self._seen.clear()
        day = date.today().isoformat()
        directory = self.transcript_root / self._safe(session)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{day}.jsonl"
        row = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "role": role,
            "name": name or ("Bot" if role == "assistant" else "群友"),
            "text": text[:2000],
        }
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("[AI bot diary] 写入聊天记录失败: %s", exc)

    def _read_transcript(self, session: str, day: str):
        path = self.transcript_root / self._safe(session) / f"{day}.jsonl"
        if not path.exists():
            return "", []
        rows = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except Exception as exc:
            logger.warning("[AI bot diary] 读取聊天记录失败: %s", exc)
            return "", []
        people = []
        for row in rows:
            name = str(row.get("name") or "").strip()
            if name and name not in people:
                people.append(name)
        text = "\n".join(f"{row.get('name', '群友')}: {row.get('text', '')}" for row in rows)
        limit = max(1000, int(self._cfg("max_transcript_chars", 6000)))
        return text[-limit:], people

    def _has_diary(self, session: str, day: str) -> bool:
        try:
            return any(str(e.get("day")) == day for e in self.store.all(session))
        except Exception:
            return False

    async def _write_one(self, session: str, day: str):
        if self._has_diary(session, day):
            return False
        transcript, people = self._read_transcript(session, day)
        if len(transcript) < 20:
            return False
        provider = self._provider()
        if provider is None:
            logger.warning("[AI bot diary] 没有可用的模型提供商，跳过 %s", session)
            return False
        minimum, maximum = self._length_range()
        # 模块默认硬上限是 300 字；用户要求更长时同步放宽。
        diary_module.MAX_ENTRY_CHARS = max(300, maximum)
        messages = build_write_messages(self.persona, transcript, day)
        system_prompt = messages[0]["content"]
        if "60~150 字" in system_prompt:
            system_prompt = system_prompt.replace("60~150 字", f"{minimum}~{maximum} 字")
        else:
            system_prompt += f"\n\n本次日记长度要求：{minimum}~{maximum} 字。"
        messages[0]["content"] = system_prompt
        try:
            response = await provider.text_chat(
                prompt=messages[1]["content"],
                system_prompt=messages[0]["content"],
            )
            text = str(getattr(response, "completion_text", "") or "").strip()
        except Exception as exc:
            logger.warning("[AI bot diary] 生成失败（静默跳过）: %s", exc)
            return False
        if len(text) < 20 or ("作为" in text[:30] and "AI" in text[:30]):
            return False
        self.store.append(session, text, day=day, people=people)
        logger.info("[AI bot diary] 已写入 %s %s", session, day)
        return True

    async def _write_all(self, day: str):
        wrote = 0
        for directory in self.transcript_root.iterdir():
            if not directory.is_dir():
                continue
            if not (directory / f"{day}.jsonl").exists():
                continue
            session = directory.name
            try:
                if await self._write_one(session, day):
                    wrote += 1
            except Exception as exc:
                logger.warning("[AI bot diary] 处理 %s 失败: %s", session, exc)
        if wrote:
            logger.info("[AI bot diary] %s 共写入 %s 篇", day, wrote)

    async def _diary_loop(self):
        while True:
            try:
                now = datetime.now()
                hour = max(0, min(23, int(self._cfg("write_hour", 23))))
                minute = max(0, min(59, int(self._cfg("write_minute", 30))))
                today = now.date().isoformat()
                if (now.hour, now.minute) >= (hour, minute) and self._last_written_day != today:
                    await self._write_all(today)
                    self._last_written_day = today
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("[AI bot diary] 定时任务异常: %s", exc)
            await asyncio.sleep(60)

    @filter.command("写日记", alias={"日记本"})
    async def write_now(self, event: AstrMessageEvent):
        """管理员手动把当前会话今天的聊天写成一篇日记。"""
        try:
            admins = {str(x) for x in (self.context.get_config().get("admins_id", []) or [])}
        except Exception:
            admins = set()
        if admins and str(event.get_sender_id()) not in admins:
            yield event.plain_result("这个只有管理员能用。")
            return
        ok = await self._write_one(self._session_key(event), date.today().isoformat())
        yield event.plain_result("写好了。" if ok else "今天还没攒够素材，或者模型没接通。")

    @filter.event_message_type(filter.EventMessageType.ALL, priority=sys.maxsize - 2)
    async def record_all_messages(self, event: AstrMessageEvent):
        """先于群聊增强插件记录群消息，保证日记有当天的上下文。"""
        if not bool(self._cfg("enabled", True)):
            return
        try:
            text = (event.get_message_str() or "").strip()
            if not text or text.startswith(("/", "!", "#")):
                return
            try:
                if str(event.get_sender_id()) == str(event.get_self_id()):
                    return
            except Exception:
                pass
            session = self._session_key(event)
            name = event.get_sender_name() or "群友"
            message_id = str(getattr(getattr(event, "message_obj", None), "message_id", "") or "")
            self._record(session, "user", name, text, message_id)
        except Exception:
            pass

    @filter.on_llm_request(priority=30)
    async def on_llm_request(self, event: AstrMessageEvent, request: ProviderRequest):
        if not bool(self._cfg("enabled", True)):
            return
        try:
            session = self._session_key(event)
            text = event.get_message_str() or ""
            name = event.get_sender_name() or "群友"
            message_id = str(getattr(getattr(event, "message_obj", None), "message_id", "") or "")
            self._record(session, "user", name, text, message_id)
            entries = self.store.recall(
                session,
                text=text,
                name=name,
                limit=max(1, min(5, int(self._cfg("recall_limit", 2)))),
            )
            block = build_recall_block(entries)
            if block:
                request.system_prompt = (request.system_prompt or "") + block
        except Exception as exc:
            logger.warning("[AI bot diary] 召回失败（已忽略）: %s", exc)

    @filter.on_llm_response(priority=-100)
    async def on_llm_response(self, event: AstrMessageEvent, response):
        if not bool(self._cfg("enabled", True)):
            return
        try:
            text = str(getattr(response, "completion_text", "") or "").strip()
            if text:
                session = self._session_key(event)
                self._record(session, "assistant", "Bot", text)
        except Exception:
            pass

    async def terminate(self):
        try:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        except Exception:
            pass
