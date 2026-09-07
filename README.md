# Storemesh — Data Engineer Technical Assignment

ETL pipeline ที่ดึงข้อมูลร้านค้าดิบจาก `shopdata.db` ทำความสะอาด
และโหลดเข้า `analytics.db` เพื่อใช้คำนวณ Customer Lifetime Value (CLV)

## Project Structure

├── data/shopdata.db # ฐานข้อมูลต้นทาง
├── sql/exploration.sql # SQL สำรวจคุณภาพข้อมูล
├── sql/clv_report.sql # SQL คำนวณ CLV
├── src/transforms.py # ฟังก์ชัน transform (pure, testable)
├── src/pipeline.py # Prefect ETL flow
├── tests/test_pipeline.py # Unit tests
├── requirements.txt
└── README.md

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python -m src.pipeline                                  # รัน ETL
pytest -v                                               # รัน unit tests
sqlite3 data/shopdata.db < sql/exploration.sql          # สำรวจข้อมูลดิบ
sqlite3 -header -column analytics.db < sql/clv_report.sql  # ดูรายงาน CLV
```

## Data Quality Findings

| ปัญหาที่พบ | จำนวน | วิธีจัดการ |
|---|---|---|
| ลูกค้าซ้ำ | _X_ | เก็บ record ที่ `signup_date` ล่าสุด |
| อีเมลว่าง / NULL | _X_ | แทนด้วย `unknown@domain.com` |
| เบอร์โทรหลาย format | _X_ | ตัดเหลือตัวเลขล้วนด้วย regex |
| เบอร์โทรมีตัวอักษร | _X_ | ถอดตัวอักษรออก เหลือเฉพาะตัวเลข |
| `total_amount <= 0` | _X_ | ตัดออกก่อนโหลดเข้า `fct_orders` |
| ไม่มีอัตราแลกเปลี่ยน | _X_ | ใช้ rate = 1.0 (ถือเป็น USD) |

> แทนค่า _X_ ด้วยตัวเลขจริงที่ได้จาก `exploration.sql`

## Design Decisions

- **Dedupe key** ใช้ชื่อเต็มแบบ normalize (trim + lowercase) เพราะอีเมลบางรายเป็น NULL จึงใช้เป็น key ไม่ได้
- **แยก `transforms.py` ออกจาก `pipeline.py`** เพื่อให้ unit test ทำงานกับ dummy data ได้โดยไม่ต้องพึ่ง database
- **`if_exists="replace"`** ในขั้น load เพื่อให้ pipeline idempotent รันซ้ำได้ผลเหมือนเดิม
- **Prefect retries** ตั้งไว้ที่ task extract เพราะเป็นจุดที่พึ่งพา I/O ภายนอก

## Assumptions

- CLV นับเฉพาะ order สถานะ `COMPLETED`
- Order ที่หา exchange rate ไม่เจอถือว่ายอดเป็น USD อยู่แล้ว (ตาม spec ของโจทย์)
- ลูกค้าที่ไม่มี order จะไม่ปรากฏในรายงาน CLV (ใช้ `INNER JOIN`)
