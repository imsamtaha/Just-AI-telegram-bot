"""ATLAS risk guide: deterministic, read-only Telegram study commands."""
from __future__ import annotations

import json
from pathlib import Path

REFERENCE_ID = "atlas-risk-management-tut-v3-20261018"
REFERENCE_FILE = Path(__file__).resolve().parent / "knowledge" / "risk_management_v3.json"
RISK_COMMANDS = {"/risk", "/atlasrisk"}
ALIASES = {"rr": "reward", "r:r": "reward", "stop": "trident", "sl": "trident", "position": "sizing", "drawdowns": "drawdown"}


def risk_command_response(user_text: str) -> str | None:
    """Reply only to /risk [topic] and /atlasrisk [topic]; never trade or query broker."""
    command, _, rest = user_text.strip().partition(" ")
    if command.lower().split("@", 1)[0] not in RISK_COMMANDS:
        return None
    try:
        payload = json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))
        if payload.get("reference_id") != REFERENCE_ID:
            raise ValueError("Reference mismatch")
        topics = payload["topics"]
    except (OSError, ValueError, KeyError, TypeError):
        return "مرجع ATLAS التعليمي غير متاح حالياً. لا توجد أي تغييرات على نظام المخاطر."

    key = rest.strip().lower().split(" ", 1)[0] if rest.strip() else ""
    key = ALIASES.get(key, key)
    if not key or key in {"help", "topics"}:
        menu = "\n".join(f"• {item['key']}: {item['title_ar']}" for item in topics)
        return (
            "📘 ATLAS | دليل إدارة المخاطر V3\n"
            "ملخّص تعليمي من ملف 40 صفحة، للمراجعة وللمحاكاة فقط.\n\n"
            f"{menu}\n\nاكتب /risk trident أو /risk leverage مثلاً."
        )
    topic = next((row for row in topics if row.get("key") == key), None)
    if topic is None:
        return "الموضوع غير موجود. اكتب /risk لعرض فهرس الدليل."
    return (
        f"📘 {topic['title_ar']}\n"
        f"المرجع: Risk Management tut V3.pdf | الصفحات {topic['pages']}\n\n"
        f"{topic['summary_ar']}\n\n"
        "ملاحظة: محتوى تعليمي وليس توصية تداول أو تعديلًا لقواعد ATLAS."
    )
