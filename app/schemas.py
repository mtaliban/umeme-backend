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


# ── Daily (PUT bulk — backward compat) ───────────────────────────────────────

class DailyLineIn(BaseModel):
    variant_id: str
    qty: int
    selling: int


class DailyIn(BaseModel):
    lines: list[DailyLineIn] = []
    expenses: list[dict] = []


# ── Daily (per-line API) ──────────────────────────────────────────────────────

class DailyLineAdd(BaseModel):
    model_config = ConfigDict(extra="allow")

    variant_id: str | None = None   # None = nje ya stock
    name: str | None = None         # lazima kama variant_id ni None
    qty: int = 1
    selling: int = 0
    buying: int = 0                 # lazima kama variant_id ni None


class DailyLineEdit(BaseModel):
    qty: int | None = None
    selling: int | None = None
    buying: int | None = None       # kwa nje ya stock peke yake


class DailyExpenseAdd(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    amount: int


class DailyExpenseEdit(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    amount: int | None = None


# ── Receipts ──────────────────────────────────────────────────────────────────

class CustomerIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = ""
    phone: str = ""


class ReceiptItemIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    variant_id: str | None = None   # None = nje ya stock
    name: str | None = None         # lazima kama variant_id ni None
    qty: int = 1
    price: int = 0
    discount: int = 0
    buying: int = 0                 # lazima kama variant_id ni None


class ReceiptIn(BaseModel):
    customer: CustomerIn
    items: list[ReceiptItemIn]
