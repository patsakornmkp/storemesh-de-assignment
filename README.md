# Storemesh — Data Engineer Technical Assignment

ETL pipeline ดึงข้อมูลร้านค้าดิบจาก `shopdata.db` ทำความสะอาด
แล้วโหลดเข้า `analytics.db` เพื่อคำนวณ Customer Lifetime Value (CLV)

## Project Structure

```
├── data/shopdata.db        # ฐานข้อมูลต้นทาง
├── sql/exploration.sql     # SQL สำรวจคุณภาพข้อมูล
├── sql/clv_report.sql      # SQL คำนวณ CLV
├── src/transforms.py       # ฟังก์ชัน transform (pure, testable)
├── src/pipeline.py         # Prefect ETL flow
├── tests/test_pipeline.py  # Unit tests
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python -m src.pipeline    # รัน ETL -> analytics.db
pytest -v                 # รัน unit tests
```

ดูรายงาน CLV:
```bash
python -c "import sqlite3,pandas as pd;c=sqlite3.connect('analytics.db');print(pd.read_sql(open('sql/clv_report.sql').read(),c))"
```

## Data Quality Findings

จากการรัน `sql/exploration.sql` บนข้อมูลดิบ (customers 12 แถว, orders 20 แถว, fx_rates 15 แถว)

| ปัญหาที่พบ | จำนวน | วิธีจัดการ |
|---|---|---|
| ลูกค้าซ้ำ (`customer_id` 1, 2) | 2 แถว | เก็บ record ที่ `signup_date` ล่าสุด → เหลือ 10 แถว |
| อีเมล NULL | 2 | แทนด้วย `unknown@domain.com` |
| เบอร์โทร NULL | 2 | คงเป็น NULL |
| เบอร์โทรมีตัวอักษร (`1-800-555-DINO`, `Ext 444`) | 2 | ถอดอักขระที่ไม่ใช่ตัวเลขออกด้วย regex |
| `total_amount <= 0` (order 103, 113, 114) | 3 | ตัดออกก่อนโหลด → เหลือ 17 แถว |
| status ไม่ใช่ COMPLETED | 4 | คงไว้ใน `fct_orders` แต่กรองออกในรายงาน CLV |
| `currency` เป็น NULL (order 107, 116) | 2 | ถือเป็น USD |
| `order_date` เป็น NULL (order 117) | 1 | คงไว้ แต่หา FX rate ไม่ได้ → ใช้ fallback |
| Orphan orders (`customer_id = 99`) | 2 | ถูกตัดออกโดย `INNER JOIN` ในรายงาน CLV |

## ⚠️ ข้อสังเกตสำคัญ: FX rate ครอบคลุมไม่ครบช่วง

| ชุดข้อมูล | ช่วงวันที่ |
|---|---|
| `vw_raw_orders` | 2023-05-01 → 2023-05-14 |
| `vw_exchange_rates` | 2023-05-01 → **2023-05-05** |

Order สกุลเงินต่างประเทศตั้งแต่ 2023-05-06 เป็นต้นไปจึงหา rate ไม่เจอ
ตาม spec ให้ใช้ rate = 1.0 ซึ่งทำให้ **order 115 (JPY 25,000)
ถูกแปลงเป็น $25,000 แทนที่จะเป็นราว $175** และดัน CLV ของ
Charlie Brown สูงผิดปกติ

จึงเพิ่มคอลัมน์ `fx_rate_matched` ใน `fct_orders` เพื่อให้ตรวจสอบได้
และ log จำนวนแถวที่ใช้ fallback ทุกครั้งที่รัน

**ข้อเสนอแนะระยะยาว:** ใช้ *most recent rate on or before order_date*
(forward-fill) แทนการ join แบบตรงวัน เพื่อให้มูลค่าสะท้อนความจริงมากขึ้น

## Design Decisions

- **Dedupe key ใช้ `customer_id`** เพราะข้อมูลจริงซ้ำที่ระดับ ID (อีเมลบางแถวเป็น NULL จึงใช้เป็น key ไม่ได้)
- **แยก `transforms.py` ออกจาก `pipeline.py`** เพื่อให้ unit test ทำงานกับ dummy data ได้โดยไม่ต้องพึ่ง database
- **`if_exists="replace"`** ในขั้น load ทำให้ pipeline idempotent รันซ้ำได้ผลเหมือนเดิม
- **Prefect retries** ตั้งไว้เฉพาะ task `extract_view` ซึ่งเป็นจุดที่พึ่งพา I/O ภายนอก
- **ไม่กรอง status ในขั้น transform** เพื่อคงข้อมูลไว้ใน fact table ให้วิเคราะห์ cancellation rate ได้ในอนาคต

## Assumptions

- CLV นับเฉพาะ order สถานะ `COMPLETED`
- Order ที่หา exchange rate ไม่เจอถือว่ายอดเป็น USD อยู่แล้ว (ตาม spec)
- ลูกค้าที่ไม่มี order สถานะ COMPLETED จะไม่ปรากฏในรายงาน CLV
