"""Bidhaa: orodha, kuongeza, kubadilisha jina, kufuta na kuongeza aina."""

from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth import current_shop_id
from ..db import db
from ..schemas import ProductIn, ProductPatch, VariantIn
from ..services import stock
from ..tz import now, today_str

router = APIRouter(tags=["products"])


@router.get("/products")
async def list_products(sid=Depends(current_shop_id)):
    out = []
    async for product in db.products.find({"shop_id": sid}).sort("created_at", 1):
        out.append(stock.product_out(product))
    return out


@router.post("/products")
async def create_product(body: ProductIn, sid=Depends(current_shop_id)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Andika jina la bidhaa")
    name_lc = name.lower()
    if await db.products.find_one({"shop_id": sid, "name_lc": name_lc}, {"_id": 1}):
        raise HTTPException(409, "Jina hili lipo tayari")

    for value in (body.qty, body.buying, body.selling):
        if int(value) < 0:
            raise HTTPException(400, "Namba si sahihi")

    ts = now()
    variants = []
    if not body.has_types:
        variants.append(stock.new_variant(name, body.qty, body.buying, body.selling, ts))

    extra = stock.clean_extra(
        body.model_dump(exclude={"name", "has_types", "qty", "buying", "selling"}),
        stock.PRODUCT_KEYS,
    )
    doc = {
        "shop_id": sid,
        "name": name,
        "name_lc": name_lc,
        "has_types": bool(body.has_types),
        "variants": variants,
        "created_at": ts,
        "updated_at": ts,
        **extra,
    }
    result = await db.products.insert_one(doc)
    doc["_id"] = result.inserted_id

    if variants and int(variants[0]["qty"]) > 0:
        variant = variants[0]
        await stock.log_movement(
            sid,
            doc["_id"],
            variant["_id"],
            variant["name"],
            variant["qty"],
            variant["qty"],
            variant["buying"],
            "new",
            None,
            today_str(),
        )

    return stock.product_out(doc)


@router.patch("/products/{product_id}")
async def rename_product(product_id: str, body: ProductPatch, sid=Depends(current_shop_id)):
    product = await stock.find_product(sid, product_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Andika jina la bidhaa")
    name_lc = name.lower()
    duplicate = await db.products.find_one(
        {"shop_id": sid, "name_lc": name_lc, "_id": {"$ne": product["_id"]}}, {"_id": 1}
    )
    if duplicate:
        raise HTTPException(409, "Jina hili lipo tayari")

    update = {"name": name, "name_lc": name_lc, "updated_at": now()}
    variants = product.get("variants", [])
    if not product.get("has_types") and variants:
        variants[0]["name"] = name
        variants[0]["name_lc"] = name_lc
        update["variants"] = variants

    await db.products.update_one({"_id": product["_id"]}, {"$set": update})
    product.update(update)
    return stock.product_out(product)


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: str, sid=Depends(current_shop_id)):
    product = await stock.find_product(sid, product_id)
    for variant in product.get("variants", []):
        qty = int(variant.get("qty", 0))
        if qty <= 0:
            continue
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
    await db.products.delete_one({"_id": product["_id"]})
    return Response(status_code=204)


@router.post("/products/{product_id}/variants", status_code=201)
async def add_variant(product_id: str, body: VariantIn, sid=Depends(current_shop_id)):
    product = await stock.find_product(sid, product_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Andika jina la aina")
    name_lc = name.lower()
    if any(v.get("name_lc") == name_lc for v in product.get("variants", [])):
        raise HTTPException(409, "Aina hii ipo tayari")
    for value in (body.qty, body.buying, body.selling):
        if int(value) < 0:
            raise HTTPException(400, "Namba si sahihi")

    extra = stock.clean_extra(
        body.model_dump(exclude={"name", "qty", "buying", "selling"}),
        stock.VARIANT_KEYS,
    )
    variant = stock.new_variant(name, body.qty, body.buying, body.selling, now(), extra)
    # Bidhaa isiyo na aina inakuwa na aina: ya zamani inabaki ya kwanza.
    await db.products.update_one(
        {"_id": product["_id"]},
        {
            "$push": {"variants": variant},
            "$set": {"updated_at": now(), "has_types": True},
        },
    )
    if int(variant["qty"]) > 0:
        await stock.log_movement(
            sid,
            product["_id"],
            variant["_id"],
            variant["name"],
            variant["qty"],
            variant["qty"],
            variant["buying"],
            "new",
            None,
            today_str(),
        )
    product.setdefault("variants", []).append(variant)
    return stock.variant_out(product, variant)
