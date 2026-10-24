"""AstrBot 鎻掍欢锛氱粰銆屽ぇ鑲ラ奔銆嶅姞涓婁細鑷繁鍐欐棩璁扮殑璁板繂銆?
渚濊禆鍚岀洰褰曠殑 dafeiyu_diary.py锛堟爣鍑嗗簱瀹炵幇锛夈€?"""

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

from . import dafeiyu_diary as diary_module
from .dafeiyu_diary import DiaryStore, build_recall_block, build_write_messages


@register(
    "astrbot_plugin_dafeiyu_diary",
    "DSH",
    "A private daily-diary memory plugin for AstrBot's Dafeiyu persona.",
    "1.0.0",
    "https://github.com/GBHBY11/astrbot-plugin-AI-diary",
)
class DafeiyuDiaryPlugin(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.config = config or {}
        self.data_dir = Path(StarTools.get_data_dir("astrbot_plugin_dafeiyu_diary"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store = DiaryStore(str(self.data_dir / "diary"))
        self.transcript_root = self.data_dir / "transcripts"
        self.transcript_root.mkdir(parents=True, exist_ok=True)
        self.persona = self._read_persona()
        self._last_written_day = ""
        self._seen: set[str] = set()
        self._task = asyncio.create_task(self._diary_loop())
        logger.info("[澶ц偉楸兼棩璁癩 宸插姞杞斤紝鏁版嵁鐩綍=%s", self.data_dir)

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
            return "浣犳槸澶ц偉楸硷紝涓€鏉″偛濞囥€佸槾纭績杞殑钃濊壊灏忛哺楸笺€?

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
            "name": name or ("澶ц偉楸? if role == "assistant" else "缇ゅ弸"),
            "text": text[:2000],
        }
        try:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("[澶ц偉楸兼棩璁癩 鍐欏叆鑱婂ぉ璁板綍澶辫触: %s", exc)

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
            logger.warning("[澶ц偉楸兼棩璁癩 璇诲彇鑱婂ぉ璁板綍澶辫触: %s", exc)
            return "", []
        people = []
        for row in rows:
            name = str(row.get("name") or "").strip()
            if name and name not in people:
                people.append(name)
        text = "\n".join(f"{row.get('name', '缇ゅ弸')}: {row.get('text', '')}" for row in rows)
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
            logger.warning("[澶ц偉楸兼棩璁癩 娌℃湁鍙敤鐨勬ā鍨嬫彁渚涘晢锛岃烦杩?%s", session)
            return False
        minimum, maximum = self._length_range()
        # 妯″潡榛樿纭笂闄愭槸 300 瀛楋紱鐢ㄦ埛瑕佹眰鏇撮暱鏃跺悓姝ユ斁瀹姐€?        diary_module.MAX_ENTRY_CHARS = max(300, maximum)
        messages = build_write_messages(self.persona, transcript, day)
        system_prompt = messages[0]["content"]
        if "60~150 瀛? in system_prompt:
            system_prompt = system_prompt.replace("60~150 瀛?, f"{minimum}~{maximum} 瀛?)
        else:
            system_prompt += f"\n\n鏈鏃ヨ闀垮害瑕佹眰锛歿minimum}~{maximum} 瀛椼€?
        messages[0]["content"] = system_prompt
        try:
            response = await provider.text_chat(
                prompt=messages[1]["content"],
                system_prompt=messages[0]["content"],
            )
            text = str(getattr(response, "completion_text", "") or "").strip()
        except Exception as exc:
            logger.warning("[澶ц偉楸兼棩璁癩 鐢熸垚澶辫触锛堥潤榛樿烦杩囷級: %s", exc)
            return False
        if len(text) < 20 or ("浣滀负" in text[:30] and "AI" in text[:30]):
            return False
        self.store.append(session, text, day=day, people=people)
        logger.info("[澶ц偉楸兼棩璁癩 宸插啓鍏?%s %s", session, day)
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
                logger.warning("[澶ц偉楸兼棩璁癩 澶勭悊 %s 澶辫触: %s", session, exc)
        if wrote:
            logger.info("[澶ц偉楸兼棩璁癩 %s 鍏卞啓鍏?%s 绡?, day, wrote)

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
                logger.warning("[澶ц偉楸兼棩璁癩 瀹氭椂浠诲姟寮傚父: %s", exc)
            await asyncio.sleep(60)

    @filter.command("鍐欐棩璁?, alias={"鏃ヨ鏈?})
    async def write_now(self, event: AstrMessageEvent):
        """绠＄悊鍛樻墜鍔ㄦ妸褰撳墠浼氳瘽浠婂ぉ鐨勮亰澶╁啓鎴愪竴绡囨棩璁般€?""
        try:
            admins = {str(x) for x in (self.context.get_config().get("admins_id", []) or [])}
        except Exception:
            admins = set()
        if admins and str(event.get_sender_id()) not in admins:
            yield event.plain_result("杩欎釜鍙湁绠＄悊鍛樿兘鐢ㄣ€?)
            return
        ok = await self._write_one(self._session_key(event), date.today().isoformat())
        yield event.plain_result("鍐欏ソ浜嗐€? if ok else "浠婂ぉ杩樻病鏀掑绱犳潗锛屾垨鑰呮ā鍨嬫病鎺ラ€氥€?)

    @filter.event_message_type(filter.EventMessageType.ALL, priority=sys.maxsize - 2)
    async def record_all_messages(self, event: AstrMessageEvent):
        """鍏堜簬缇よ亰澧炲己鎻掍欢璁板綍缇ゆ秷鎭紝淇濊瘉鏃ヨ鏈夊綋澶╃殑涓婁笅鏂囥€?""
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
            name = event.get_sender_name() or "缇ゅ弸"
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
            name = event.get_sender_name() or "缇ゅ弸"
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
            logger.warning("[澶ц偉楸兼棩璁癩 鍙洖澶辫触锛堝凡蹇界暐锛? %s", exc)

    @filter.on_llm_response(priority=-100)
    async def on_llm_response(self, event: AstrMessageEvent, response):
        if not bool(self._cfg("enabled", True)):
            return
        try:
            text = str(getattr(response, "completion_text", "") or "").strip()
            if text:
                session = self._session_key(event)
                self._record(session, "assistant", "澶ц偉楸?, text)
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

