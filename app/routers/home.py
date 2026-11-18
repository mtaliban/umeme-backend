"""Nyumbani: faida halisi, stock na vilivyouzwa leo."""

from fastapi import APIRouter, Depends

from ..auth import current_shop_id
from ..db import db
from ..services import summary as summary_service
from ..tz import parse_day

router = APIRouter(tags=["home"])


@router.get("/home")
async def home(date: str | None = None, sid=Depends(current_shop_id)):
    day = parse_day(date).isoformat()
    sold_by_variant = await summary_service.sold_variants(sid, day)

    products = []
    async for product in db.products.find({"shop_id": sid}).sort("created_at", 1):
        variants = []
        for variant in product.get("variants", []):
            vid = str(variant["_id"])
            sold = sold_by_variant.get(vid, {"qty": 0, "profit": 0})
            variants.append(
                {
                    "id": vid,
                    "product_id": str(product["_id"]),
                    "product_name": product["name"],
                    "name": variant["name"],
                    "qty": int(variant.get("qty", 0)),
                    "buying": int(variant.get("buying", 0)),
                    "selling": int(variant.get("selling", 0)),
                    "sold_today": int(sold["qty"]),
                    "profit_today": int(sold["profit"]),
                }
            )
        products.append(
            {
                "id": str(product["_id"]),
                "name": product["name"],
                "has_types": bool(product.get("has_types", True)),
                "variants": variants,
            }
        )

    return {
        "date": day,
        "summary": await summary_service.day_summary(sid, day),
        "products": products,
        "sold_today": await summary_service.sold_items(sid, day),
    }
