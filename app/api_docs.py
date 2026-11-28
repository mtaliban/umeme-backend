"""Miundo ya majibu inayoonekana kwenye /docs (sehemu 1-5).

Models hizi ni za NYARAKA pekee: hazitumiki kwenye runtime, kwa hiyo hazibadilishi
majibu yoyote. Zinaonyesha fields kamili ambazo app inasoma, ili /docs isiwe tupu.
"""

from pydantic import BaseModel

# ── Mzunguko wa siku ──────────────────────────────────────────────────────────


class DaySummary(BaseModel):
    sales: int
    capital: int
    expenses: int
    product_profit: int
    net: int


class DailyLine(BaseModel):
    id: str
    variant_id: str | None = None
    product_id: str | None = None
    name: str
    qty: int
    selling: int
    buying: int
    stock_selling: int | None = None
    stock_taken: int = 0
    out_of_stock: bool = False
    receipt_no: str | None = None
    receipt_id: str | None = None


class DailyReceiptLine(BaseModel):
    id: str
    receipt_id: str
    receipt_no: str
    number: str | None = None
    variant_id: str | None = None
    product_id: str | None = None
    name: str
    qty: int
    price: int
    discount: int = 0
    selling: int
    buying: int
    stock_taken: int = 0
    amount: int
    out_of_stock: bool = False


class DailyExpenseRow(BaseModel):
    id: str
    name: str
    amount: int


class DaySheet(BaseModel):
    date: str
    lines: list[DailyLine]
    receipt_lines: list[DailyReceiptLine]
    expenses: list[DailyExpenseRow]
    saved_at: str | None = None
    summary: DaySummary


class CalendarOut(BaseModel):
    month: str
    label: str
    today: str
    days: list[str]
    has_prev: bool
    has_next: bool


# ── Ripoti ────────────────────────────────────────────────────────────────────


class ReportExpenseRow(BaseModel):
    name: str
    amount: int


class ReportProductRow(BaseModel):
    name: str
    qty: int
    sales: int
    capital: int
    profit: int


class ReportTotals(BaseModel):
    qty: int
    sales: int
    profit: int


class DayReport(BaseModel):
    period: str
    date: str
    label: str
    short_label: str | None = None
    has_prev: bool
    has_next: bool
    summary: DaySummary
    expenses: list[ReportExpenseRow]
    products: list[ReportProductRow]
    totals: ReportTotals


class ReportBar(BaseModel):
    key: str
    label: str
    name: str
    sales: int | None = None
    capital: int | None = None
    expenses: int | None = None
    net: int | None = None


class ReportTopRow(BaseModel):
    name: str
    qty: int
    profit: int


class ReportUnsoldRow(BaseModel):
    name: str
    qty: int
    capital: int


class ExpenseDateRow(BaseModel):
    date: str
    name: str
    amount: int


class ExpenseGroupRow(BaseModel):
    name: str
    count: int
    amount: int


class WeekReport(BaseModel):
    period: str
    start: str
    end: str
    label: str
    short_label: str | None = None
    has_prev: bool
    has_next: bool
    summary: DaySummary
    bars: list[ReportBar]
    top: list[ReportTopRow]
    low: list[ReportTopRow]
    unsold: list[ReportUnsoldRow]
    expense_list: list[ExpenseDateRow]


class MonthReport(BaseModel):
    period: str
    start: str
    end: str
    label: str
    short_label: str | None = None
    has_prev: bool
    has_next: bool
    summary: DaySummary
    bars: list[ReportBar]
    top: list[ReportTopRow]
    low: list[ReportTopRow]
    unsold: list[ReportUnsoldRow]
    expense_groups: list[ExpenseGroupRow]


# ── Risiti ────────────────────────────────────────────────────────────────────


class ReceiptCustomer(BaseModel):
    name: str
    phone: str
    address: str
    location: str | None = None


class ReceiptItem(BaseModel):
    name: str
    category: str
    qty: int
    price: int
    discount: int
    amount: int


class ReceiptShop(BaseModel):
    name: str
    phone: str
    email: str
    signature_name: str


class Receipt(BaseModel):
    id: str
    number: str
    date: str
    time: str
    customer: ReceiptCustomer
    items: list[ReceiptItem]
    total_qty: int
    gross: int
    discount: int
    paid: int
    shop: ReceiptShop


class ReceiptListRow(BaseModel):
    id: str
    number: str
    date: str
    customer: str
    time: str
    total_qty: int
    gross: int
    discount: int
    paid: int
    shop: ReceiptShop
    location: str | None = None


class ReceiptListOut(BaseModel):
    date: str
    receipts: list[ReceiptListRow]
    count: int
    total: int
    next_number: str


class ReceiptHistoryDay(BaseModel):
    date: str
    label: str
    total: int
    receipts: list[ReceiptListRow]


class ReceiptHistoryOut(BaseModel):
    days: list[ReceiptHistoryDay]
    next_before: str | None = None


# ── Stock, nyumbani, mimi ────────────────────────────────────────────────────


class StockSummary(BaseModel):
    products: int
    variants: int
    qty: int
    capital: int


class StockProductRow(BaseModel):
    id: str
    name: str
    has_variants: bool
    variants: int
    qty: int
    capital: int


class StockOut(BaseModel):
    summary: StockSummary
    products: list[StockProductRow]


class VariantOut(BaseModel):
    id: str
    name: str
    qty: int
    buying: int
    selling: int


class ProductSummary(BaseModel):
    qty: int
    capital: int
    profit_if_sold: int


class ProductDetail(BaseModel):
    id: str
    name: str
    has_variants: bool
    summary: ProductSummary
    variants: list[VariantOut]


class HomeTopRow(BaseModel):
    name: str
    qty: int
    selling: int
    sales: int
    capital: int
    profit: int


class HomeOut(BaseModel):
    day: str
    summary: DaySummary
    top: list[HomeTopRow]
    expenses: list[ReportExpenseRow]


class MeOut(BaseModel):
    id: str
    name: str
    phone: str
    email: str
    signature_name: str


class OkOut(BaseModel):
    ok: bool


# ── Kuunganisha kwenye OpenAPI ────────────────────────────────────────────────

MODELS: dict[str, type[BaseModel]] = {
    "DaySheet": DaySheet,
    "CalendarOut": CalendarOut,
    "DayReport": DayReport,
    "WeekReport": WeekReport,
    "MonthReport": MonthReport,
    "Receipt": Receipt,
    "ReceiptListOut": ReceiptListOut,
    "ReceiptHistoryOut": ReceiptHistoryOut,
    "StockOut": StockOut,
    "ProductDetail": ProductDetail,
    "HomeOut": HomeOut,
    "MeOut": MeOut,
    "OkOut": OkOut,
}

DAY_SHEET_WRITES = {
    ("post", "/daily/{date}/lines"),
    ("patch", "/daily/{date}/lines/{line_id}"),
    ("delete", "/daily/{date}/lines/{line_id}"),
    ("post", "/daily/{date}/expenses"),
    ("patch", "/daily/{date}/expenses/{expense_id}"),
    ("delete", "/daily/{date}/expenses/{expense_id}"),
    ("post", "/daily/{date}/close"),
    ("post", "/daily/{date}/reopen"),
    ("put", "/daily/{date}"),
    ("post", "/daily/{date}/scan"),
}

RESPONSES: dict[tuple[str, str], str] = {
    ("get", "/daily/{date}"): "DaySheet",
    ("get", "/daily/calendar"): "CalendarOut",
    ("get", "/reports/day/{date}"): "DayReport",
    ("get", "/reports/week"): "WeekReport",
    ("get", "/reports/month"): "MonthReport",
    ("get", "/reports/year"): "MonthReport",
    ("post", "/receipts"): "Receipt",
    ("get", "/receipts/{receipt_id}"): "Receipt",
    ("post", "/receipts/{receipt_id}/cancel"): "Receipt",
    ("get", "/receipts"): "ReceiptListOut",
    ("get", "/receipts/history"): "ReceiptHistoryOut",
    ("get", "/stock"): "StockOut",
    ("delete", "/stock/products/{product_id}"): "StockOut",
    ("get", "/stock/products/{product_id}"): "ProductDetail",
    ("patch", "/stock/variants/{variant_id}"): "ProductDetail",
    ("delete", "/stock/variants/{variant_id}"): "ProductDetail",
    ("get", "/home"): "HomeOut",
    ("get", "/me"): "MeOut",
    ("get", "/health"): "OkOut",
    ("post", "/auth/pin"): "OkOut",
    ("put", "/auth/pin"): "OkOut",
}
RESPONSES.update({(method, path): "DaySheet" for method, path in DAY_SHEET_WRITES})


def attach(schema: dict) -> dict:
    """Weka models kwenye components na ziunganishe na kila njia."""
    components = schema.setdefault("components", {}).setdefault("schemas", {})

    # Jenga models zote (pamoja na zilizojificha ndani ya $defs).
    pending = list(MODELS.items())
    while pending:
        name, model = pending.pop()
        if name in components:
            continue
        js = model.model_json_schema(ref_template="#/components/schemas/{model}")
        for nested_name, nested in (js.pop("$defs", {}) or {}).items():
            components.setdefault(nested_name, nested)
        components[name] = js

    for (method, path), model_name in RESPONSES.items():
        operation = schema.get("paths", {}).get(path, {}).get(method)
        if not isinstance(operation, dict):
            continue
        response = operation.setdefault("responses", {}).setdefault(
            "200", {"description": "Successful Response"}
        )
        response.setdefault("content", {}).setdefault("application/json", {})["schema"] = {
            "$ref": f"#/components/schemas/{model_name}"
        }

    return schema
