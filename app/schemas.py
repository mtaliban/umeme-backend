"""Miundo ya maombi (Pydantic v2)."""

from pydantic import BaseModel, ConfigDict


class PinIn(BaseModel):
    pin: str


class PinChangeIn(BaseModel):
    old_pin: str
    new_pin: str


class DeviceIn(BaseModel):
    fcm_token: str
    platform: str = "android"


class ProductIn(BaseModel):
    """Fields za ziada (mf. supplier, note) zinahifadhiwa kama zilivyo."""

    model_config = ConfigDict(extra="allow")

    name: str
    has_types: bool = False
    qty: int = 0
    buying: int = 0
    selling: int = 0


class ProductPatch(BaseModel):
    name: str


class VariantIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    qty: int = 0
    buying: int = 0
    selling: int = 0


class VariantPatch(BaseModel):
    add_qty: int = 0
    buying: int | None = None
    selling: int | None = None
    name: str | None = None


class DailyLineIn(BaseModel):
    variant_id: str
    qty: int
    selling: int


class DailyIn(BaseModel):
    lines: list[DailyLineIn] = []
    expenses: list[dict] = []


class CustomerIn(BaseModel):
    """Maelezo ya mteja yanaweza kuwa na fields zozote za ziada."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    phone: str = ""


class ReceiptItemIn(BaseModel):
    variant_id: str
    qty: int
    price: int
    discount: int = 0


class ReceiptIn(BaseModel):
    customer: CustomerIn
    items: list[ReceiptItemIn]
