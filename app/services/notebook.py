"""Picha ya daftari: kupunguza picha, AI na kusafisha data (sehemu 3).

Funguo za AI zinasomwa kutoka .env pekee (haziko kwenye code wala git) —
kubadilisha AI ni kubadilisha `.env` na kuwasha server upya.
"""

import base64
import io
import json
import logging
import re
import time
from dataclasses import dataclass

import httpx
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from ..config import settings
from ..db import db

logger = logging.getLogger("ummu.scan")

MAX_SIDE = 1600
JPEG_QUALITY = 85

# Maneno ya kichwa cha jedwali / majumla — hayapaswi kuingia kama bidhaa.
HEADER_WORDS = {
    "jumla",
    "jumla kuu",
    "total",
    "grand total",
    "subtotal",
    "bidhaa",
    "idadi",
    "bei",
    "gharama",
    "mauzo",
    "name",
    "item",
    "items",
    "qty",
    "quantity",
    "price",
    "amount",
    "expenses",
    "expense",
}

# Maneno yasiyo na maana kwenye majina ya bidhaa (3.4).
STOPWORDS = {"ya", "za", "la", "wa", "cha", "vya"}

PROMPT = """Wewe ni msaidizi wa kusoma picha ya daftari la duka la nguo.
Soma ukurasa wote na urudishe JSON PEKEE — hakuna maelezo, hakuna ```:

{{"lines":[{{"name":"jina la bidhaa","qty":1,"price":0,"total":0,"buying":0}}],
 "expenses":[{{"name":"jina la gharama","amount":0}}]}}

Kanuni:
- "name" ni jina la bidhaa kama lilivyoandikwa; usiandike vichwa vya jedwali
  wala mistari ya "Jumla"/"Total".
- "qty" ni idadi, "price" ni bei ya kimoja, "total" ni jumla ya mstari.
- "buying" ni bei ya kununua ikiwa imeandikwa, vinginevyo 0.
- Tarehe iliyoandikwa kwenye daftari usiirudishe.
- Gharama ziwe kwenye "expenses" pekee (usafiri, bando, chakula, n.k.).
Majina ya bidhaa zilizopo kwenye stock (tumia jina lililo karibu zaidi kama
linafanana): {names}"""


@dataclass
class Provider:
    name: str
    api_key: str
    model: str


# ── Picha ─────────────────────────────────────────────────────────────────────

def shrink_image(data: bytes) -> bytes:
    """Punguza picha hadi upana/urefu 1600 na JPEG ubora 85."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        if max(image.size) > MAX_SIDE:
            image.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        image.save(out, "JPEG", quality=JPEG_QUALITY)
        return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(422, "Picha si sahihi")


# ── AI ────────────────────────────────────────────────────────────────────────

def providers() -> list[Provider]:
    """AI_PROVIDER kwanza, kisha AI_FALLBACK (iliyotenganishwa kwa koma)."""
    order = [settings.ai_provider, *(settings.ai_fallback or "").split(",")]
    out: list[Provider] = []
    seen: set[str] = set()
    for raw in order:
        name = (raw or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        if name == "gemini":
            out.append(Provider("gemini", settings.gemini_api_key, settings.gemini_model))
        elif name == "groq":
            out.append(Provider("groq", settings.groq_api_key, settings.groq_model))
        elif name in {"claude", "anthropic"}:
            out.append(Provider("claude", settings.claude_api_key, settings.claude_model))
    return out


def _prompt(names: list[str]) -> str:
    listed = ", ".join(names[:120])
    return PROMPT.format(names=listed or "-")


async def _gemini(provider: Provider, image: bytes, prompt: str) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{provider.model}:generateContent"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64.b64encode(image).decode(),
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    # x-goog-api-key (si ?key=) ili ufunguo usiandikwe kwenye URL/logs.
    async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
        res = await client.post(
            url, json=payload, headers={"x-goog-api-key": provider.api_key}
        )
        res.raise_for_status()
        data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _groq(provider: Provider, image: bytes, prompt: str) -> str:
    payload = {
        "model": provider.model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64,"
                            + base64.b64encode(image).decode()
                        },
                    },
                ],
            }
        ],
    }
    headers = {"Authorization": f"Bearer {provider.api_key}"}
    async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"]


async def _claude(provider: Provider, image: bytes, prompt: str) -> str:
    payload = {
        "model": provider.model,
        "max_tokens": 2048,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.b64encode(image).decode(),
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    headers = {
        "x-api-key": provider.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages", json=payload, headers=headers
        )
        res.raise_for_status()
        data = res.json()
    return data["content"][0]["text"]


_CALLERS = {"gemini": _gemini, "groq": _groq, "claude": _claude}


def _extract_json(text: str) -> dict:
    """AI mara nyingi huzunguka JSON kwa ``` — ondoa na some."""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("AI haikutuma JSON")
        data = json.loads(raw[start : end + 1])
    return data if isinstance(data, dict) else {}


async def read_notebook(image: bytes, names: list[str]) -> dict:
    """Mpiga AI wa kwanza anayepatikana; zote zikishindikana → 503."""
    available = [p for p in providers() if p.api_key]
    if not available:
        logger.warning("Hakuna AI iliyowekwa (AI_PROVIDER/AI_FALLBACK + funguo)")
        raise HTTPException(503, "Jaribu tena baadaye")

    prompt = _prompt(names)
    for provider in available:
        started = time.perf_counter()
        try:
            text = await _CALLERS[provider.name](provider, image, prompt)
            data = _extract_json(text)
        except Exception as exc:  # kikomo cha bure, mtandao, JSON mbovu
            logger.warning(
                "AI %s (%s) imeshindikana baada ya %.1fs: %s",
                provider.name,
                provider.model,
                time.perf_counter() - started,
                exc,
            )
            continue
        # Log ya server (si kwa mtumiaji): AI iliyotumika na muda.
        logger.info(
            "AI scan: %s (%s) — %.1fs",
            provider.name,
            provider.model,
            time.perf_counter() - started,
        )
        return data

    raise HTTPException(503, "Jaribu tena baadaye")


# ── Kusafisha data (3.4) ──────────────────────────────────────────────────────

def _int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
    try:
        return int(float(text))
    except ValueError:
        return 0


def _words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", (text or "").lower())
        if word not in STOPWORDS
    }


def match_stock(name: str, stock: list[dict]) -> dict | None:
    """Linganisha jina la daftari na Stock (maneno ya kuunganisha hayana maana)."""
    target = _words(name)
    if not target:
        return None
    best: dict | None = None
    best_score = 0.0
    for item in stock:
        for field in ("name", "product_name"):
            words = _words(item.get(field) or "")
            if not words:
                continue
            if words == target:
                return item
            common = target & words
            if not common:
                continue
            score = len(common) / max(len(target), len(words))
            if score > best_score:
                best, best_score = item, score
    return best if best_score >= 0.6 else None


def _is_header(name: str) -> bool:
    return name.strip().strip(":").lower() in HEADER_WORDS


def normalize(data: dict, stock: list[dict]) -> dict:
    """Ondoa vichwa/majumla, rekebisha namba, chuja bei na marudio."""
    lines: list[dict] = []
    seen: set[tuple] = set()
    for raw in data.get("lines") or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name or _is_header(name):
            continue

        qty = _int(raw.get("qty"))
        price = _int(raw.get("price"))
        total = _int(raw.get("total"))
        buying = _int(raw.get("buying")) if raw.get("buying") not in (None, "") else None

        # Idadi x bei isipolingana na jumla iliyoandikwa — rekebisha kutoka jumla.
        if total > 0 and qty > 0 and qty * price != total:
            price = max(1, round(total / qty))
        elif total > 0 and qty <= 0 and price > 0:
            qty = max(1, round(total / price))

        if qty <= 0:
            continue
        if price < 100:  # bei isiyowezekana
            continue

        key = (name.lower(), qty, price)
        if key in seen:  # mstari unaojirudia
            continue
        seen.add(key)

        matched = match_stock(name, stock)
        if matched:
            # Bei ya kununua inatoka Stock; stock inapungua kama kawaida.
            lines.append(
                {
                    "variant_id": matched["id"],
                    "name": matched["name"],
                    "qty": qty,
                    "selling": price,
                    "buying": int(matched.get("buying") or 0),
                    "matched": True,
                }
            )
        else:
            # Bidhaa isiyo kwenye orodha — inaingia bila kosa wala ujumbe.
            lines.append(
                {
                    "variant_id": None,
                    "name": name,
                    "qty": qty,
                    "selling": price,
                    # Bila buying ya daftari: sawa na bei ya kuuza (faida 0).
                    "buying": buying if buying and buying > 0 else price,
                    "matched": False,
                }
            )

    expenses: list[dict] = []
    for raw in data.get("expenses") or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name or _is_header(name):
            continue
        amount = _int(raw.get("amount"))
        if amount < 50:  # gharama ndogo sana zinaachwa
            continue
        expenses.append({"name": name, "amount": amount})

    return {"lines": lines, "expenses": expenses}


async def stock_names(sid) -> list[dict]:
    """Aina zote za Stock za duka hili (kwa kulinganisha majina)."""
    out: list[dict] = []
    async for product in db.products.find({"shop_id": sid}, {"name": 1, "variants": 1}):
        for variant in product.get("variants", []):
            out.append(
                {
                    "id": str(variant["_id"]),
                    "name": variant["name"],
                    "product_name": product.get("name", ""),
                    "buying": int(variant.get("buying", 0) or 0),
                    "selling": int(variant.get("selling", 0) or 0),
                }
            )
    return out
