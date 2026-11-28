"""Stock (K0–K4): orodha, bidhaa na aina — JSON kamili ya UMMU-STOCK.

Njia na JSON hapa ni zilezile za spec; collections ni zile za `/products`
(bidhaa moja na aina zake ndani ya document moja).
"""

import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from ..auth import current_shop_id
from ..db import db
from ..services import stock
from ..tz import now, today_str

router = APIRouter(prefix="/stock", tags=["stock"])

CORE_KEYS = {"_id", "shop_id", "name", "name_lc", "has_types", "variants", "created_at", "updated_at"}


def err(code: int, message: str):
    raise HTTPException(code, message)


def ci(name: str) -> dict:
    return {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}


class ProductIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    has_variants: bool = True
    qty: int | None = None
    buying: int | None = None
    selling: int | None = None


class VariantIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    qty: int | None = None
    buying: int | None = None
    selling: int | None = None


class VariantPatch(BaseModel):
    model_config = ConfigDict(extra="allow")

    qty: int | None = None          # idadi mpya KAMILI (haiongezwi)
    buying: int | None = None
    selling: int | None = None
    add_qty: int | None = None      # imeondolewa — ikipewa ni 422 "Tumia qty"


def _qty(value) -> int:
    if value is None or int(value) < 0:
        err(422, "Jaza idadi")
    return int(value)


def _buying(value) -> int:
    if value is None or int(value) < 0:
        err(422, "Jaza buying")
    return int(value)


def _selling(value) -> int:
    if value is None or int(value) < 1:
        err(422, "Jaza selling")
    return int(value)


def _extra(values: dict) -> dict:
    return {k: v for k, v in values.items() if k not in CORE_KEYS | {"has_variants"}}


def _variant_json(variant: dict) -> dict:
    return {
        "id": str(variant["_id"]),
        "name": variant["name"],
        "qty": int(variant.get("qty", 0)),
        "buying": int(variant.get("buying", 0)),
        "selling": int(variant.get("selling", 0)),
    }


def _detail(product: dict) -> dict:
    variants = sorted(
        product.get("variants", []),
        key=lambda v: (-int(v.get("qty", 0)), (v.get("name") or "").lower()),
    )
    qty = sum(max(int(v.get("qty", 0)), 0) for v in variants)
    capital = sum(max(int(v.get("qty", 0)), 0) * int(v.get("buying", 0)) for v in variants)
    profit = sum(
        max(int(v.get("qty", 0)), 0) * (int(v.get("selling", 0)) - int(v.get("buying", 0)))
        for v in variants
    )
    return {
        "id": str(product["_id"]),
        "name": product["name"],
        "has_variants": bool(product.get("has_types", True)),
        "summary": {"qty": qty, "capital": capital, "profit_if_sold": profit},
        "variants": [_variant_json(v) for v in variants],
    }


async def _product(sid, product_id: str) -> dict:
    try:
        pid = ObjectId(str(product_id))
    except Exception:
        err(404, "Haipo")
    product = await db.products.find_one({"_id": pid, "shop_id": sid})
    if not product:
        err(404, "Haipo")
    return product


def _no_variants(product: dict) -> bool:
    return not bool(product.get("has_types", True))


# ---------- K0
@router.get("")
async def stock_list(sid=Depends(current_shop_id)):
    return await stock.stock_list_payload(sid)


# ---------- K1
@router.get("/products/{product_id}")
async def product_detail(product_id: str, sid=Depends(current_shop_id)):
    return _detail(await _product(sid, product_id))


# ---------- K2
@router.post("/products")
async def add_product(body: ProductIn, sid=Depends(current_shop_id)):
    name = (body.name or "").strip()
    if not name:
        err(422, "Jaza jina")
    if await db.products.find_one({"shop_id": sid, "name": ci(name)}, {"_id": 1}):
        err(409, "Bidhaa hii ipo tayari")

    ts = now()
    has_variants = bool(body.has_variants)
    variants: list[dict] = []
    if not has_variants:
        qty = _qty(body.qty)
        buying = _buying(body.buying)
        selling = _selling(body.selling)
        variants = [stock.new_variant(name, qty, buying, selling, ts)]

    doc = {
        "shop_id": sid,
        "name": name,
        "name_lc": name.lower(),
        "has_types": has_variants,
        "variants": variants,
        "created_at": ts,
        "updated_at": ts,
        **_extra(
            body.model_dump(exclude={"name", "has_variants", "qty", "buying", "selling"})
        ),
    }
    result = await db.products.insert_one(doc)
    doc["_id"] = result.inserted_id

    if variants and qty > 0:
        variant = variants[0]
        await stock.log_movement(
            sid,
            doc["_id"],
            variant["_id"],
            variant["name"],
            qty,
            qty,
            buying,
            "new",
            None,
            today_str(),
        )
    return _detail(doc)


# ---------- K3
@router.post("/products/{product_id}/variants")
async def add_variant(product_id: str, body: VariantIn, sid=Depends(current_shop_id)):
    product = await _product(sid, product_id)
    if _no_variants(product):
        err(400, "Bidhaa hii haina aina")

    name = (body.name or "").strip()
    if not name:
        err(422, "Jaza jina")
    if any((v.get("name") or "").lower() == name.lower() for v in product.get("variants", [])):
        err(409, "Aina hii ipo tayari")

    qty = _qty(body.qty)
    buying = _buying(body.buying)
    selling = _selling(body.selling)
    variant = stock.new_variant(
        name,
        qty,
        buying,
        selling,
        now(),
        _extra(body.model_dump(exclude={"name", "qty", "buying", "selling"})),
    )
    await db.products.update_one(
        {"_id": product["_id"], "shop_id": sid},
        {"$push": {"variants": variant}, "$set": {"updated_at": now()}},
    )
    if qty > 0:
        await stock.log_movement(
            sid,
            product["_id"],
            variant["_id"],
            variant["name"],
            qty,
            qty,
            buying,
            "new",
            None,
            today_str(),
        )
    product.setdefault("variants", []).append(variant)
    return _detail(product)


# ---------- K4
@router.patch("/variants/{variant_id}")
async def edit_variant(variant_id: str, body: VariantPatch, sid=Depends(current_shop_id)):
    try:
        vid = ObjectId(str(variant_id))
    except Exception:
        err(404, "Haipo")
    product = await db.products.find_one({"shop_id": sid, "variants._id": vid})
    if not product:
        err(404, "Haipo")
    variant = next(v for v in product.get("variants", []) if v["_id"] == vid)

    # Sehemu 1.1: idadi inayotumwa ni idadi mpya kamili.
    if body.add_qty is not None:
        err(422, "Tumia qty")
    qty = _qty(body.qty) if body.qty is not None else None
    buying = _buying(body.buying) if body.buying is not None else None
    selling = _selling(body.selling) if body.selling is not None else None

    sets: dict = {"updated_at": now()}
    if buying is not None:
        sets["variants.$.buying"] = buying
    if selling is not None:
        sets["variants.$.selling"] = selling
    if qty is not None:
        sets["variants.$.qty"] = qty

    await db.products.update_one(
        {"_id": product["_id"], "shop_id": sid, "variants._id": vid}, {"$set": sets}
    )

    # Mwendo wa stock ni TOFAUTI (delta), si idadi mpya: 5 -> 1 huandikwa -4.
    if qty is not None:
        delta = qty - int(variant.get("qty", 0))
        if delta != 0:
            await stock.log_movement(
                sid,
                product["_id"],
                vid,
                variant["name"],
                delta,
                qty,
                buying if buying is not None else int(variant.get("buying", 0)),
                "restock" if delta > 0 else "adjust",
                None,
                today_str(),
            )

    product = await _product(sid, str(product["_id"]))
    return _detail(product)


# ---------- K5 — kufuta aina moja
@router.delete("/variants/{variant_id}")
async def delete_variant(variant_id: str, sid=Depends(current_shop_id)):
    try:
        vid = ObjectId(str(variant_id))
    except Exception:
        err(404, "Haipo")
    product = await db.products.find_one({"shop_id": sid, "variants._id": vid})
    if not product:
        err(404, "Haipo")
    if _no_variants(product):
        err(400, "Futa bidhaa nzima")

    # Aina na mwendo wake wa stock peke yake; historia ya mauzo haiguswi.
    await db.products.update_one(
        {"_id": product["_id"], "shop_id": sid},
        {"$pull": {"variants": {"_id": vid}}, "$set": {"updated_at": now()}},
    )
    await db.stock_movements.delete_many({"shop_id": sid, "variant_id": vid})

    return _detail(await _product(sid, str(product["_id"])))


# ---------- K6 — kufuta bidhaa nzima
@router.delete("/products/{product_id}")
async def delete_product(product_id: str, sid=Depends(current_shop_id)):
    product = await _product(sid, product_id)
    variant_ids = [v["_id"] for v in product.get("variants", [])]
    if variant_ids:
        await db.stock_movements.delete_many(
            {"shop_id": sid, "variant_id": {"$in": variant_ids}}
        )
    # Historia ya mauzo na risiti HAIGUSWI (mistari ya zamani inabaki).
    await db.products.delete_one({"_id": product["_id"], "shop_id": sid})
    return await stock_list(sid)
