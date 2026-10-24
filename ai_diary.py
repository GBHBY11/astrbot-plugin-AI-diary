"""
AI bot diary — a minimal private-diary implementation for AstrBot.

依赖：只用标准库（json / os / re / datetime）。
不依赖 embedding：DeepSeek 官方没有 /embeddings 接口，所以召回用
「昵称精确匹配 + 关键词子串 + 时间衰减」，够用且零成本。

用法：
    from ai_diary import DiaryStore, write_daily, build_recall_block

    store = DiaryStore("data/diary")
    write_daily(store, complete=my_llm_call, group_id="123456",
                transcript=今天的聊天记录, date="2026-10-24")

    recall = build_recall_block(store.recall("123456", text=用户这句话, name="张三"))
    # recall 直接拼进 system prompt 末尾，空字符串表示没有可提的日记

CLI 自测（不联网，用假 LLM）：
    python ai_diary.py --demo
"""

from __future__ import annotations

import json
import os
import re
from datetime import date as _date, datetime

# ── 写日记的提示词 ──────────────────────────────────────────────────────────

DIARY_SYSTEM = """你在替角色写她自己的日记。日记只有她自己看，不是发给群里的消息。

写法硬要求：
1. 第一人称，日期开头单独一行，例如「10月24日 周五 阴」。
2. 全文 60~150 字，3~6 个短句，可以不成段。
3. 必须落到一件具体的事上：谁说了什么、谁干了什么。不写「今天聊了很多」这种空话。
4. 必须带一点情绪，而且情绪要藏在动作或抱怨里，不要直接写「我很开心」。
5. 允许嘴硬、允许自我辩解、允许写到一半改口。允许出现「算了」「不写了」这种收尾。
6. 禁止：总结腔（今天收获很大）、列点、书面语、任何 AI 自述、把聊天记录复述一遍。
7. 涉及隐私（手机号、身份证、住址、密码）一律不写。可以不写人名，用「那家伙」代替。
8. 不要每篇都提到吃和胖，那是口癖不是日记。

只输出日记正文，不要解释，不要加标题符号。"""


def build_write_messages(persona: str, transcript: str, day: str) -> list[dict]:
    """构造写日记的 messages。transcript 是当天聊天记录（会被截断）。"""
    transcript = (transcript or "").strip()
    if len(transcript) > 6000:
        transcript = transcript[-6000:]
    return [
        {"role": "system", "content": DIARY_SYSTEM + "\n\n【人设参考】\n" + persona.strip()},
        {
            "role": "user",
            "content": (
                f"今天是 {day}。下面是今天群里的聊天记录，"
                f"挑你真正在意的一两件写进日记：\n\n{transcript}\n\n只输出日记正文。"
            ),
        },
    ]


# ── 存储 ────────────────────────────────────────────────────────────────────

_PRIVACY = [
    (re.compile(r"1[3-9]\d{9}"), "[号码]"),
    (re.compile(r"\d{17}[\dXx]"), "[证件]"),
    (re.compile(r"(?i)(password|passwd|密码)\s*[:=：]?\s*\S+"), "[密码]"),
]

MAX_ENTRY_CHARS = 300


def _scrub(text: str) -> str:
    for pat, repl in _PRIVACY:
        text = pat.sub(repl, text)
    return text.strip()[:MAX_ENTRY_CHARS]


class DiaryStore:
    """按群隔离的日记库：data/diary/<group_id>/<YYYY-MM>.jsonl

    群与群之间物理隔离，私聊用 group_id="private_<qq>"，不会串味。
    """

    def __init__(self, root: str = "data/diary"):
        self.root = root

    def _dir(self, group_id: str) -> str:
        safe = re.sub(r"[^\w\-]", "_", str(group_id))
        return os.path.join(self.root, safe)

    def append(self, group_id: str, text: str, day: str | None = None,
               people: list[str] | None = None, tags: list[str] | None = None,
               mood: str = "") -> dict:
        day = day or _date.today().isoformat()
        entry = {
            "day": day,
            "ts": datetime.now().isoformat(timespec="seconds"),
            "mood": mood,
            "people": people or [],
            "tags": tags or [],
            "text": _scrub(text),
        }
        d = self._dir(group_id)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, day[:7] + ".jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def _files(self, group_id: str, months: int = 2) -> list[str]:
        d = self._dir(group_id)
        if not os.path.isdir(d):
            return []
        files = sorted(f for f in os.listdir(d) if f.endswith(".jsonl"))
        return [os.path.join(d, f) for f in files[-months:]]

    def all(self, group_id: str) -> list[dict]:
        out: list[dict] = []
        for path in self._files(group_id):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue  # 半行写入/手改坏了就跳过，别让日记炸掉机器人
        return out

    def recent(self, group_id: str, n: int = 3) -> list[dict]:
        return self.all(group_id)[-n:]

    def recall(self, group_id: str, text: str = "", name: str = "",
               limit: int = 2) -> list[dict]:
        """召回：优先命中当前说话人，其次关键词，最后给最近一篇垫底。"""
        entries = self.all(group_id)
        if not entries:
            return []
        scored: list[tuple[float, dict]] = []
        for i, e in enumerate(entries):
            score = 0.0
            if name and (name in e.get("people", []) or name in e.get("text", "")):
                score += 5.0
            for kw in _keywords(text):
                if kw and kw in e.get("text", ""):
                    score += 1.5
            if score:
                score += i / max(len(entries), 1)  # 同样相关时，新的优先
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [e for _, e in scored[:limit]]
        if not picked:
            picked = entries[-1:]
        return picked


_STOP = set("的了吗呢吧啊呀我就你也他她它在是有不这那个和说道要会能可以一下什么怎么还有")


def _keywords(text: str, limit: int = 6) -> list[str]:
    """极简关键词：连续汉字 2~6 字 + 英文单词。不引 jieba，够用。"""
    if not text:
        return []
    words = re.findall(r"[\u4e00-\u9fa5]{2,6}|[A-Za-z][A-Za-z0-9_]{2,}", text)
    out: list[str] = []
    for w in words:
        if w in _STOP or any(ch in _STOP for ch in w):
            continue
        if w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


# ── 写一篇（带调用方注入的 LLM） ────────────────────────────────────────────

def write_daily(store: DiaryStore, complete, group_id: str, transcript: str,
                persona: str = "", day: str | None = None,
                people: list[str] | None = None) -> dict | None:
    """complete(messages) -> str 由调用方提供（OpenAI/DeepSeek SDK 皆可）。

    调用失败或输出不像日记时返回 None，绝不把异常抛到聊天链路里。
    """
    day = day or _date.today().isoformat()
    try:
        raw = complete(build_write_messages(persona, transcript, day)) or ""
    except Exception:
        return None
    text = raw.strip().strip("`").strip()
    if len(text) < 20 or "作为" in text[:20] and "AI" in text[:20]:
        return None
    return store.append(group_id, text, day=day, people=people or [])


# ── 拼进 system prompt ─────────────────────────────────────────────────────

RECALL_RULE = (
    "\n\n【你的日记】下面是你在自己日记本里写过的东西，只有你知道。"
    "聊天时不要背日记、不要提「我写了日记」。"
    "只有在真的接得上时才顺口带一句（比如「上次你还说……」），"
    "几十条对话里最多提一次。记错细节是正常的，但别编新事实。\n"
)


def build_recall_block(entries: list[dict]) -> str:
    if not entries:
        return ""
    body = "\n".join(f"- {e['text']}" for e in entries)
    return RECALL_RULE + body


def build_weekly_messages(entries: list[dict], day: str) -> list[dict]:
    """周记：把 7 篇压成 1 篇，防止上下文无限膨胀。"""
    body = "\n\n".join(e["text"] for e in entries)
    return [
        {"role": "system", "content": DIARY_SYSTEM},
        {"role": "user", "content": (
            f"这是 {day} 这一周的日记。把它们压成一篇周记，100 字以内，"
            f"保留最有情绪的那件事，其余忘掉：\n\n{body}\n\n只输出正文。"
        )},
    ]


# ── 自测 ───────────────────────────────────────────────────────────────────

def _demo() -> None:
    import shutil

    # 建在工作目录下，避免某些环境把系统临时目录设成不可写
    root = os.path.join(os.getcwd(), "_diary_demo")
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root, exist_ok=True)
    store = DiaryStore(root)
    assert store.recall("g1") == [], "空库应返回空"

    fake = lambda msgs: "10月24日 周五 阴\n那家伙又喊我大肥鱼。没理他。\n后来还是帮他看了报错，顺手的事。\n不写了，去吃饭。"
    e = write_daily(store, fake, "g1", "张三: 大肥鱼 帮我看个报错",
                    persona="你是大肥鱼", day="2026-10-24", people=["张三"])
    assert e and "大肥鱼" in e["text"], e

    # 隐私脱敏
    store.append("g1", "他手机 13812345678，我记下了", day="2026-10-24")
    assert "13812345678" not in store.all("g1")[-1]["text"]

    # 跨群隔离
    assert store.all("g2") == []

    # 召回命中说话人
    got = store.recall("g1", text="又说我胖", name="张三")
    assert got and "大肥鱼" in got[0]["text"], got
    block = build_recall_block(got)
    assert "【你的日记】" in block

    # 无关键词时垫底给最近一篇
    assert store.recall("g1", text="今天天气不错")

    # LLM 挂了不抛异常
    boom = lambda msgs: (_ for _ in ()).throw(RuntimeError("api down"))
    assert write_daily(store, boom, "g3", "随便聊聊") is None

    # 垃圾输出被拒
    assert write_daily(store, lambda m: "作为 AI，我无法写日记。", "g4", "x") is None

    print("demo ok ->", root)
    for e in store.all("g1"):
        print("-", e["text"].replace("\n", " / "))
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--demo" in sys.argv:
        _demo()
    else:
        print(__doc__)
