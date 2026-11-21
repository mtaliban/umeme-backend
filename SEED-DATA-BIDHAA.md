# UMMU AYMAN — Data za kuanzia (seed) kwa FastAPI

> **Kwa AI ya backend:** faili hili lina bidhaa zote zinazoonekana kwenye picha za app (makundi 16, aina 37) pamoja na mfano wa risiti na mauzo ya leo. Ziingize kwenye server **kupitia API zilizopo** (Njia A, inapendekezwa) au **moja kwa moja MongoDB** (Njia B). Majina ya fields ni yale yale ya `API-FASTAPI-MONGODB.md`.

Server: `http://13.60.24.131`  ·  PIN ya duka: ile iliyowekwa na `scripts/create_shop.py`

## 1. Muhtasari

| Kitu | Idadi |
|---|---|
| Bidhaa (makundi) | 16 (15 zenye aina + 1 bila aina) |
| Aina zote | 37 |
| Idadi ya stock yote | 264 |
| Mtaji uliopo dukani (Σ qty × buying) | 3,383,500 |
| Faida ukiuza zote (Σ qty × (selling − buying)) | 1,571,500 |

## 2. Bidhaa zote

| Bidhaa | Aina | Idadi | Buying | Selling | Mtaji |
|---|---|---|---|---|---|
| Kanzu | Alfurqan Kanzu | 8 | 50,000 | 65,000 | 400,000 |
| Kanzu | Kanzu ya Oman | 6 | 30,000 | 40,000 | 180,000 |
| Kanzu | Kanzu ya Saudia | 10 | 10,000 | 15,000 | 100,000 |
| Kanzu | Kanzu watoto | 12 | 8,000 | 12,000 | 96,000 |
| Abaya | Abaya ya Kituruki | 16 | 5,000 | 8,000 | 80,000 |
| Abaya | Abaya nyeusi | 5 | 7,000 | 11,000 | 35,000 |
| Abaya | Abaya ya harusi | 3 | 40,000 | 60,000 | 120,000 |
| Abaya | Abaya ya Dubai | 8 | 25,000 | 35,000 | 200,000 |
| Kofia | Kofia nyeupe | 8 | 20,000 | 25,000 | 160,000 |
| Kofia | Kofia nyeusi | 6 | 15,000 | 22,000 | 90,000 |
| Kofia | Kofia ya bao | 5 | 6,000 | 10,000 | 30,000 |
| Viatu | Viatu vya kufunga | 7 | 25,000 | 35,000 | 175,000 |
| Viatu | Viatu vya ngozi | 4 | 35,000 | 50,000 | 140,000 |
| Viatu | Raba | 9 | 18,000 | 26,000 | 162,000 |
| Sandals | Sandals za ngozi | 6 | 9,000 | 14,000 | 54,000 |
| Sandals | Sandals za wanawake | 5 | 7,000 | 11,000 | 35,000 |
| Kanga | Kanga za pwani | 10 | 6,000 | 9,000 | 60,000 |
| Kanga | Kanga za harusi | 4 | 15,000 | 22,000 | 60,000 |
| Hijab | Hijab za chiffon | 12 | 4,000 | 7,000 | 48,000 |
| Hijab | Hijab za jezi | 9 | 3,500 | 6,000 | 31,500 |
| Baibui | Baibui jeusi | 5 | 18,000 | 26,000 | 90,000 |
| Baibui | Baibui la Oman | 3 | 30,000 | 42,000 | 90,000 |
| Dera | Dera la Somali | 7 | 12,000 | 18,000 | 84,000 |
| Dera | Dera la kawaida | 6 | 8,000 | 12,000 | 48,000 |
| Jalabia | Jalabia za kiume | 4 | 20,000 | 30,000 | 80,000 |
| Jalabia | Jalabia za kike | 5 | 18,000 | 27,000 | 90,000 |
| Suruali | Suruali za kitambaa | 8 | 12,000 | 18,000 | 96,000 |
| Suruali | Jeans | 6 | 15,000 | 23,000 | 90,000 |
| T-shirt | T-shirt za kawaida | 10 | 5,000 | 8,000 | 50,000 |
| T-shirt | Polo | 5 | 9,000 | 14,000 | 45,000 |
| Mikoba | Mkoba wa ngozi | 3 | 30,000 | 45,000 | 90,000 |
| Mikoba | Mkoba mdogo | 4 | 10,000 | 16,000 | 40,000 |
| Manukato | Udi | 6 | 15,000 | 25,000 | 90,000 |
| Manukato | Marashi | 9 | 6,000 | 10,000 | 54,000 |
| Tasbihi | Tasbihi za mbao | 12 | 2,000 | 4,000 | 24,000 |
| Tasbihi | Tasbihi za lulu | 6 | 5,000 | 9,000 | 30,000 |
| Mafuta ya nywele | Mafuta ya nywele | 12 | 3,000 | 5,000 | 36,000 |

`Mafuta ya nywele` ni mfano wa bidhaa **isiyo na aina** (`has_types: false`).

## 3. JSON kamili (`products.json`)

Hifadhi hii kama `scripts/products.json`:
```json
[
  {
    "name": "Kanzu",
    "has_types": true,
    "variants": [
      {
        "name": "Alfurqan Kanzu",
        "qty": 8,
        "buying": 50000,
        "selling": 65000
      },
      {
        "name": "Kanzu ya Oman",
        "qty": 6,
        "buying": 30000,
        "selling": 40000
      },
      {
        "name": "Kanzu ya Saudia",
        "qty": 10,
        "buying": 10000,
        "selling": 15000
      },
      {
        "name": "Kanzu watoto",
        "qty": 12,
        "buying": 8000,
        "selling": 12000
      }
    ]
  },
  {
    "name": "Abaya",
    "has_types": true,
    "variants": [
      {
        "name": "Abaya ya Kituruki",
        "qty": 16,
        "buying": 5000,
        "selling": 8000
      },
      {
        "name": "Abaya nyeusi",
        "qty": 5,
        "buying": 7000,
        "selling": 11000
      },
      {
        "name": "Abaya ya harusi",
        "qty": 3,
        "buying": 40000,
        "selling": 60000
      },
      {
        "name": "Abaya ya Dubai",
        "qty": 8,
        "buying": 25000,
        "selling": 35000
      }
    ]
  },
  {
    "name": "Kofia",
    "has_types": true,
    "variants": [
      {
        "name": "Kofia nyeupe",
        "qty": 8,
        "buying": 20000,
        "selling": 25000
      },
      {
        "name": "Kofia nyeusi",
        "qty": 6,
        "buying": 15000,
        "selling": 22000
      },
      {
        "name": "Kofia ya bao",
        "qty": 5,
        "buying": 6000,
        "selling": 10000
      }
    ]
  },
  {
    "name": "Viatu",
    "has_types": true,
    "variants": [
      {
        "name": "Viatu vya kufunga",
        "qty": 7,
        "buying": 25000,
        "selling": 35000
      },
      {
        "name": "Viatu vya ngozi",
        "qty": 4,
        "buying": 35000,
        "selling": 50000
      },
      {
        "name": "Raba",
        "qty": 9,
        "buying": 18000,
        "selling": 26000
      }
    ]
  },
  {
    "name": "Sandals",
    "has_types": true,
    "variants": [
      {
        "name": "Sandals za ngozi",
        "qty": 6,
        "buying": 9000,
        "selling": 14000
      },
      {
        "name": "Sandals za wanawake",
        "qty": 5,
        "buying": 7000,
        "selling": 11000
      }
    ]
  },
  {
    "name": "Kanga",
    "has_types": true,
    "variants": [
      {
        "name": "Kanga za pwani",
        "qty": 10,
        "buying": 6000,
        "selling": 9000
      },
      {
        "name": "Kanga za harusi",
        "qty": 4,
        "buying": 15000,
        "selling": 22000
      }
    ]
  },
  {
    "name": "Hijab",
    "has_types": true,
    "variants": [
      {
        "name": "Hijab za chiffon",
        "qty": 12,
        "buying": 4000,
        "selling": 7000
      },
      {
        "name": "Hijab za jezi",
        "qty": 9,
        "buying": 3500,
        "selling": 6000
      }
    ]
  },
  {
    "name": "Baibui",
    "has_types": true,
    "variants": [
      {
        "name": "Baibui jeusi",
        "qty": 5,
        "buying": 18000,
        "selling": 26000
      },
      {
        "name": "Baibui la Oman",
        "qty": 3,
        "buying": 30000,
        "selling": 42000
      }
    ]
  },
  {
    "name": "Dera",
    "has_types": true,
    "variants": [
      {
        "name": "Dera la Somali",
        "qty": 7,
        "buying": 12000,
        "selling": 18000
      },
      {
        "name": "Dera la kawaida",
        "qty": 6,
        "buying": 8000,
        "selling": 12000
      }
    ]
  },
  {
    "name": "Jalabia",
    "has_types": true,
    "variants": [
      {
        "name": "Jalabia za kiume",
        "qty": 4,
        "buying": 20000,
        "selling": 30000
      },
      {
        "name": "Jalabia za kike",
        "qty": 5,
        "buying": 18000,
        "selling": 27000
      }
    ]
  },
  {
    "name": "Suruali",
    "has_types": true,
    "variants": [
      {
        "name": "Suruali za kitambaa",
        "qty": 8,
        "buying": 12000,
        "selling": 18000
      },
      {
        "name": "Jeans",
        "qty": 6,
        "buying": 15000,
        "selling": 23000
      }
    ]
  },
  {
    "name": "T-shirt",
    "has_types": true,
    "variants": [
      {
        "name": "T-shirt za kawaida",
        "qty": 10,
        "buying": 5000,
        "selling": 8000
      },
      {
        "name": "Polo",
        "qty": 5,
        "buying": 9000,
        "selling": 14000
      }
    ]
  },
  {
    "name": "Mikoba",
    "has_types": true,
    "variants": [
      {
        "name": "Mkoba wa ngozi",
        "qty": 3,
        "buying": 30000,
        "selling": 45000
      },
      {
        "name": "Mkoba mdogo",
        "qty": 4,
        "buying": 10000,
        "selling": 16000
      }
    ]
  },
  {
    "name": "Manukato",
    "has_types": true,
    "variants": [
      {
        "name": "Udi",
        "qty": 6,
        "buying": 15000,
        "selling": 25000
      },
      {
        "name": "Marashi",
        "qty": 9,
        "buying": 6000,
        "selling": 10000
      }
    ]
  },
  {
    "name": "Tasbihi",
    "has_types": true,
    "variants": [
      {
        "name": "Tasbihi za mbao",
        "qty": 12,
        "buying": 2000,
        "selling": 4000
      },
      {
        "name": "Tasbihi za lulu",
        "qty": 6,
        "buying": 5000,
        "selling": 9000
      }
    ]
  },
  {
    "name": "Mafuta ya nywele",
    "has_types": false,
    "variants": [
      {
        "name": "Mafuta ya nywele",
        "qty": 12,
        "buying": 3000,
        "selling": 5000
      }
    ]
  }
]
```

## 4. Njia A — kuingiza kupitia API (inapendekezwa)

Mpangilio wa maombi kwa kila bidhaa:

**Bidhaa yenye aina** (mf. Kanzu):
```http
POST /products
Authorization: Bearer <token>
{"name": "Kanzu", "has_types": true}
→ 201 {"id": "<product_id>", ...}

POST /products/<product_id>/variants
{"name": "Alfurqan Kanzu", "qty": 8, "buying": 50000, "selling": 65000}
POST /products/<product_id>/variants
{"name": "Kanzu ya Oman", "qty": 6, "buying": 30000, "selling": 40000}
... (aina zote za bidhaa hiyo)
```

**Bidhaa isiyo na aina:**
```http
POST /products
{"name": "Mafuta ya nywele", "has_types": false, "qty": 12, "buying": 3000, "selling": 5000}
```

Token: `POST /auth/pin {"pin": "1234"}` → `{"token": "..."}`

### Script: `scripts/seed_via_api.py`
```python
"""Ingiza bidhaa zote + (hiari) risiti 2 na mauzo ya leo kupitia API.
Matumizi:
  pip install httpx
  python scripts/seed_via_api.py --url http://13.60.24.131 --pin 1234            # bidhaa tu
  python scripts/seed_via_api.py --url http://13.60.24.131 --pin 1234 --demo     # + risiti + mauzo ya leo
"""
import argparse, json, pathlib, datetime, httpx

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://13.60.24.131")
ap.add_argument("--pin", required=True)
ap.add_argument("--demo", action="store_true", help="ongeza risiti 2 na mauzo ya leo ya mfano")
a = ap.parse_args()

c = httpx.Client(base_url=a.url, timeout=30)
r = c.post("/auth/pin", json={"pin": a.pin}); r.raise_for_status()
c.headers["Authorization"] = "Bearer " + r.json()["token"]

def ok(r):
    if r.status_code >= 400:
        raise SystemExit(f"{r.request.method} {r.request.url} -> {r.status_code} {r.text}")
    return r.json() if r.content else None

existing = {p["name"].lower(): p for p in ok(c.get("/products"))}
products = json.loads((pathlib.Path(__file__).parent / "products.json").read_text(encoding="utf-8"))
vid = {}  # jina la aina -> variant_id

for p in products:
    if p["name"].lower() in existing:                     # usirudie kama ipo tayari
        print("ipo tayari:", p["name"])
        for v in existing[p["name"].lower()]["variants"]:
            vid[v["name"]] = v["id"]
        continue
    if not p["has_types"]:
        v = p["variants"][0]
        prod = ok(c.post("/products", json={"name": p["name"], "has_types": False,
                                             "qty": v["qty"], "buying": v["buying"], "selling": v["selling"]}))
        vid[v["name"]] = prod["variants"][0]["id"]
    else:
        prod = ok(c.post("/products", json={"name": p["name"], "has_types": True}))
        for v in p["variants"]:
            nv = ok(c.post(f"/products/{prod['id']}/variants", json=v))
            vid[v["name"]] = nv["id"]
    print("imeingia:", p["name"], len(p["variants"]), "aina")

if a.demo:
    receipts = [
        {"customer": {"name": "Abuu Firdaus", "phone": "0754 112 233"},
         "items": [{"variant_id": vid["Alfurqan Kanzu"], "qty": 2, "price": 65000, "discount": 0},
                   {"variant_id": vid["Kofia nyeupe"], "qty": 1, "price": 25000, "discount": 0}]},
        {"customer": {"name": "Mwanaisha Juma", "phone": "0715 220 330"},
         "items": [{"variant_id": vid["Abaya ya Kituruki"], "qty": 2, "price": 8000, "discount": 0}]},
    ]
    for rc in receipts:
        print("risiti:", ok(c.post("/receipts", json=rc))["number"])
    today = datetime.date.today().isoformat()
    daily = {
        "lines": [{"variant_id": vid["Kofia nyeusi"], "qty": 2, "selling": 22000},
                  {"variant_id": vid["Viatu vya kufunga"], "qty": 3, "selling": 33000}],
        "expenses": [{"name": "Usafirishaji", "amount": 2000},
                     {"name": "Bando", "amount": 1000, "mtandao": "Vodacom"}],
    }
    s = ok(c.put(f"/daily/{today}", json=daily))["summary"]
    print("mauzo ya leo:", s)

print("Tayari. Stock yote:", sum(v["qty"] for p in ok(c.get("/products")) for v in p["variants"]))
```

## 5. Data za mfano (hiari, `--demo`)

**Risiti 2** — `POST /receipts`
```json
{"customer": {"name": "Abuu Firdaus", "phone": "0754 112 233"},
 "items": [{"variant_id": "<Alfurqan Kanzu>", "qty": 2, "price": 65000, "discount": 0},
           {"variant_id": "<Kofia nyeupe>",   "qty": 1, "price": 25000, "discount": 0}]}
```
```json
{"customer": {"name": "Mwanaisha Juma", "phone": "0715 220 330"},
 "items": [{"variant_id": "<Abaya ya Kituruki>", "qty": 2, "price": 8000, "discount": 0}]}
```

**Mauzo ya leo (daftari)** — `PUT /daily/<leo>`
```json
{"lines": [{"variant_id": "<Kofia nyeusi>",      "qty": 2, "selling": 22000},
           {"variant_id": "<Viatu vya kufunga>", "qty": 3, "selling": 33000}],
 "expenses": [{"name": "Usafirishaji", "amount": 2000},
              {"name": "Bando", "amount": 1000, "mtandao": "Vodacom"}]}
```
`<...>` = `id` ya aina hiyo kutoka `GET /products`.

## 6. Matokeo yanayotarajiwa (kagua hivi)

**Baada ya bidhaa tu:**
- `GET /products` → bidhaa 16, aina 37, Σ qty = **264**
- `GET /home` → Stock 264, `summary` zote 0
- `GET /reports/week` → `capital_in_shop` = **3,383,500**

**Baada ya `--demo`:**

| | Mauzo | Mtaji | Faida ya bidhaa |
|---|---|---|---|
| Risiti 0001 (Abuu) | 155,000 | 120,000 | 35,000 |
| Risiti 0002 (Mwanaisha) | 16,000 | 10,000 | 6,000 |
| Daftari (Kofia nyeusi 2, Viatu 3) | 143,000 | 105,000 | 38,000 |
| **Jumla** | **314,000** | **235,000** | **79,000** |

- Gharama = 3,000 → **Faida halisi = 76,000**
- `GET /home` → Stock **254** (264 − 10), Vilivyouzwa leo **10**
- `GET /daily/<leo>` → `receipt_lines` 3, `lines` 2, `summary.net` = 76,000
- Ukiendesha `PUT /daily/<leo>` ile ile tena → Stock inabaki **254** (si 249)

## 7. Njia B — moja kwa moja MongoDB (kama API bado haijakamilika)

```python
"""python scripts/seed_mongo.py  (tumia .env ile ile ya server)"""
import json, pathlib, datetime, os
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
shop = db.shops.find_one()
assert shop, "Kwanza endesha scripts/create_shop.py"
sid = shop["_id"]; now = datetime.datetime.utcnow(); today = datetime.date.today().isoformat()
for p in json.loads((pathlib.Path(__file__).parent / "products.json").read_text(encoding="utf-8")):
    if db.products.find_one({"shop_id": sid, "name_lc": p["name"].lower()}):
        print("ipo tayari:", p["name"]); continue
    pid = ObjectId(); variants = []
    for v in p["variants"]:
        vid = ObjectId()
        variants.append({"_id": vid, "name": v["name"], "name_lc": v["name"].lower(), "qty": v["qty"],
                          "buying": v["buying"], "selling": v["selling"], "created_at": now})
        db.stock_movements.insert_one({"shop_id": sid, "product_id": pid, "variant_id": vid, "name": v["name"],
            "change": v["qty"], "qty_after": v["qty"], "buying": v["buying"], "reason": "new",
            "ref_id": None, "date": today, "at": now})
    db.products.insert_one({"_id": pid, "shop_id": sid, "name": p["name"], "name_lc": p["name"].lower(),
                             "has_types": p["has_types"], "variants": variants, "created_at": now, "updated_at": now})
    print("imeingia:", p["name"])
```
Njia B inaingiza bidhaa tu. Risiti na mauzo ya leo ziingizwe kupitia API (Njia A `--demo`) ili namba za risiti, stock na hesabu zifanyike sawasawa.

## 8. Kufuta data za mfano
Ukitaka kuanza upya na bidhaa halisi za duka:
```python
db.products.delete_many({"shop_id": sid}); db.stock_movements.delete_many({"shop_id": sid})
db.receipts.delete_many({"shop_id": sid}); db.daily_sheets.delete_many({"shop_id": sid})
db.shops.update_one({"_id": sid}, {"$set": {"receipt_seq": 0}})
```
