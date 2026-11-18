"""Aina (variants): kubadilisha, kufuta na kutafuta."""

import re

from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth import current_shop_id
from ..db import db
from ..schemas import VariantPatch
from ..services import stock
from ..tz import now, today_str

router = APIRouter(tags=["variants"])


async def _read(sid, product_id, variant_id):
    product = await db.products.find_one({"_id": product_id, "shop_id": sid})
    variant = next((v for v in (product or {}).get("variants", []) if v["_id"] == variant_id), None)
    return product, variant


@router.patch("/variants/{variant_id}")
async def patch_variant(variant_id: str, body: VariantPatch, sid=Depends(current_shop_id)):
    product, variant = await stock.find_variant(sid, variant_id)
    pid = product["_id"]
    vid = variant["_id"]
    sets: dict = {"updated_at": now()}
    new_name = variant["name"]

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Andika jina la aina")
        name_lc = name.lower()
        if any(v["_id"] != vid and v.get("name_lc") == name_lc for v in product.get("variants", [])):
            raise HTTPException(409, "Aina hii ipo tayari")
        new_name = name
        sets["variants.$.name"] = name
        sets["variants.$.name_lc"] = name_lc
        if not product.get("has_types"):
            sets["name"] = name
            sets["name_lc"] = name_lc

    for field in ("buying", "selling"):
        value = getattr(body, field)
        if value is not None:
            if int(value) < 0:
                raise HTTPException(400, "Bei si sahihi")
            sets[f"variants.$.{field}"] = int(value)

    add_qty = int(body.add_qty or 0)
    buying = int(body.buying if body.buying is not None else variant.get("buying", 0) or 0)

    if add_qty < 0:
        res = await db.products.update_one(
            {
                "_id": pid,
                "shop_id": sid,
                "variants": {"$elemMatch": {"_id": vid, "qty": {"$gte": abs(add_qty)}}},
            },
            {"$inc": {"variants.$.qty": add_qty}, "$set": {"updated_at": now()}},
        )
        if res.modified_count == 0:
            current = await stock.variant_qty(sid, pid, vid)
            raise HTTPException(400, f"{variant['name']}: zipo {current} tu")
    elif add_qty > 0:
        await db.products.update_one(
            {"_id": pid, "shop_id": sid, "variants._id": vid},
            {"$inc": {"variants.$.qty": add_qty}, "$set": {"updated_at": now()}},
        )

    if any(k.startswith("variants.$.") for k in sets):
        await db.products.update_one(
            {"_id": pid, "shop_id": sid, "variants._id": vid}, {"$set": sets}
        )

    if add_qty != 0:
        qty_after = await stock.variant_qty(sid, pid, vid)
        await stock.log_movement(
            sid,
            pid,
            vid,
            new_name,
            add_qty,
            qty_after,
            buying,
            "restock",
            None,
            today_str(),
        )

    product, variant = await _read(sid, pid, vid)
    if not product or not variant:
        raise HTTPException(404, "Bidhaa haipo")
    return stock.variant_out(product, variant)


@router.delete("/variants/{variant_id}", status_code=204)
async def delete_variant(variant_id: str, sid=Depends(current_shop_id)):
    product, variant = await stock.find_variant(sid, variant_id)
    qty = int(variant.get("qty", 0))
    if qty > 0:
        await stock.log_movement(
            sid,
            product["_id"],
            variant["_id"],
            variant["name"],
            -qty,
            0,
            variant.get("buying", 0),
            "delete",
            None,
            today_str(),
        )
    await db.products.update_one(
        {"_id": product["_id"]},
        {"$pull": {"variants": {"_id": variant["_id"]}}, "$set": {"updated_at": now()}},
    )
    remaining = [v for v in product.get("variants", []) if v["_id"] != variant["_id"]]
    if not remaining:
        await db.products.delete_one({"_id": product["_id"]})
    return Response(status_code=204)


@router.get("/variants/search")
async def search_variants(q: str = "", sid=Depends(current_shop_id)):
    query = (q or "").strip().lower()
    tokens = [re.escape(token) for token in query.split() if token]
    if not tokens:
        return []
    # Kila neno liwe mwanzo wa neno fulani: "aba ny" → "Abaya nyeusi"
    pattern = "".join(f"(?=.*\\b{token})" for token in tokens)
    pipeline = [
        {"$match": {"shop_id": sid, "variants.name_lc": {"$regex": pattern}}},
        {"$unwind": "$variants"},
        {"$match": {"variants.name_lc": {"$regex": pattern}}},
        {"$limit": 10},
        {"$project": {"product_name": "$name", "variant": "$variants"}},
    ]
    out = []
    async for doc in db.products.aggregate(pipeline):
        variant = doc["variant"]
        out.append(
            {
                "id": str(variant["_id"]),
                "product_id": str(doc["_id"]),
                "product_name": doc["product_name"],
                "name": variant["name"],
                "qty": int(variant.get("qty", 0)),
                "buying": int(variant.get("buying", 0)),
                "selling": int(variant.get("selling", 0)),
            }
        )
    return out
