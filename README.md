# DAPTrax API

Backend API untuk **DAPTrax**, aplikasi pencatatan keuangan pribadi dengan fitur:

- Admin login lokal (1 admin)
- User login dengan Google
- Manajemen category per user
- Manajemen account per user
- Pencatatan transaksi income / expense
- Transfer antar account
- Summary keuangan
- Account balance summary
- Audit log
- Backup import / export CSV

---

## Tech Stack

- **FastAPI**
- **SQLAlchemy 2.0**
- **Alembic**
- **PostgreSQL (Neon)**
- **Authlib** (Google OAuth)
- **Pwdlib Argon2** (password hashing)
- **Vercel** (deployment)

---

## Core Business Rules

### Authentication

- Hanya ada **1 admin**
- Admin login menggunakan **local/password**
- User biasa dibuat melalui **Google Login**
- User biasa **tidak** dibuat manual oleh admin

### Financial Data

- `transaction_type` hanya:
  - `income`
  - `expense`
- `category` adalah label bebas milik masing-masing user
- `account` adalah akun bebas milik masing-masing user
- transfer antar account disimpan di tabel **terpisah** agar tidak mengganggu summary income/expense

### Account Balance

- `initial_balance` = saldo awal saat account dibuat
- `initial_balance` **tidak berubah otomatis**
- `current_balance` dihitung dinamis:

```text
current_balance =
    initial_balance
    + total_income
    - total_expense
    + total_transfer_in
    - total_transfer_out
```
