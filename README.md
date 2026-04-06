<div align="center">

# DAPTrax API

Backend API for **DAPTrax** — a personal finance tracking application built with a clean, secure, and scalable API-first architecture.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)](https://neon.tech/)
[![Alembic](https://img.shields.io/badge/Alembic-Database%20Migrations-4B5563)](https://alembic.sqlalchemy.org/)
[![Authlib](https://img.shields.io/badge/Authlib-Google%20OAuth-4285F4?logo=google&logoColor=white)](https://docs.authlib.org/)
[![Deploy](https://img.shields.io/badge/Deploy-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com/)
[![License](https://img.shields.io/badge/License-Private-informational)](#)

A secure backend focused on **personal finance recording**, **user-based data isolation**, **dynamic balance calculation**, and **clean deployment on Vercel + Neon**.

</div>

---

## Overview

DAPTrax API is the backend service for a personal finance application with support for:

- Local admin authentication
- Google OAuth for regular users
- Per-user category management
- Per-user account management
- Income and expense transaction recording
- Transfer between accounts
- Financial summary endpoints
- Dynamic account balance summary
- Audit logging
- CSV import/export backup

The project is designed for a **small-scale but secure** use case, prioritizing simplicity, maintainability, and strong business-rule enforcement.

---

## Screenshots

> Replace these placeholder images with actual screenshots from your project later.

### Dashboard / Summary

![Dashboard Screenshot](./assets/dashboard-placeholder.png)

### Transactions Module

![Transactions Screenshot](./assets/transactions-placeholder.png)

### Admin / User Management

![Admin Screenshot](./assets/admin-placeholder.png)

---

## Highlights

- **API-first architecture** for separated frontend and backend
- **Single local admin** with dedicated management privileges
- **Google login** for end users
- **Strict per-user ownership validation** for financial data
- **Dynamic account balance calculation** based on actual transaction flow
- **Separate transfer storage** to avoid polluting income/expense summaries
- **Audit log support** for sensitive actions
- **Vercel + Neon friendly** deployment design

---

## Tech Stack

- **FastAPI**
- **SQLAlchemy 2.0**
- **Alembic**
- **PostgreSQL (Neon)**
- **Authlib** for Google OAuth
- **Pwdlib Argon2** for password hashing
- **Vercel** for deployment

---

## Core Business Rules

### Authentication

- There is only **one admin**
- Admin logs in using **local/password authentication**
- Regular users are created through **Google Login**
- Regular users are **not created manually by admin**

### Financial Data

- `transaction_type` only supports:
  - `income`
  - `expense`
- `category` is a free label owned by each user
- `account` is a user-owned financial container
- Transfers between accounts are stored in a **separate table** so they do not interfere with income/expense summaries

### Account Balance

- `initial_balance` is the starting amount when an account is created
- `initial_balance` does **not** change automatically
- `current_balance` is calculated dynamically:

```text
current_balance =
    initial_balance
    + total_income
    - total_expense
    + total_transfer_in
    - total_transfer_out
```

---

## Security Principles

This backend is designed with practical security defaults for finance-related workflows:

- Password hashing with **Argon2**
- **HttpOnly cookie-based session/auth strategy**
- Backend-controlled authorization and ownership checks
- Rate limiting for sensitive authentication flows
- Strong separation between **admin** and **user** capabilities
- Audit logging for critical actions
- CORS configured explicitly for allowed frontend origins
- No dependency on storing tokens in `localStorage`

---

## Architecture Snapshot

```text
Frontend (SvelteKit)
        |
        v
   DAPTrax API (FastAPI)
        |
        v
 PostgreSQL (Neon)
```

### Suggested responsibility split

**Frontend**

- UI rendering
- Dashboard / forms / charts / calendar
- Calls backend API only

**Backend**

- Authentication and authorization
- Business rules
- Validation
- Transaction and summary logic
- Admin features

**Database**

- Persistent storage
- Aggregation-friendly finance data
- Balance and summary source of truth

---

## Project Structure

```bash
app/
├── api/
├── core/
├── models/
├── repositories/
├── schemas/
├── services/
└── utils/

alembic/
requirements.txt
vercel.json
```

A more complete version may look like this:

```bash
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   └── utils/
├── alembic/
├── tests/
├── requirements.txt
└── vercel.json
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
APP_NAME=daptrax-api
APP_ENV=development
APP_DEBUG=true

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require
DATABASE_URL_MIGRATIONS=postgresql+psycopg://USER:PASSWORD@HOST.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require

FRONTEND_URL=http://localhost:5173
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
SESSION_SECRET=
```

---

## Local Development

### 1. Create virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" alembic pydantic-settings python-dotenv authlib pwdlib
pip freeze > requirements.txt
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start development server

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Open API docs

```text
http://127.0.0.1:8000/docs
```

---

## Deployment

### Recommended stack

- **Frontend**: Vercel
- **Backend**: Vercel Functions (FastAPI)
- **Database**: Neon PostgreSQL

### Vercel notes

- Use **pooled connection** for runtime
- Use **direct connection** for Alembic migrations
- Keep backend request/response oriented
- Avoid heavy long-running background jobs on free/serverless setup

---

## Roadmap

- [x] Backend foundation with FastAPI + Neon
- [x] Migration setup with Alembic
- [ ] Admin local authentication
- [ ] Google OAuth login
- [ ] Categories module
- [ ] Accounts module
- [ ] Transactions module
- [ ] Transfers module
- [ ] Financial summaries
- [ ] Audit logs
- [ ] CSV import/export backup
- [ ] Frontend integration

---

## Notes

This README is intentionally written in a GitHub-friendly format so it can be used directly for:

- GitHub repository landing page
- GitLab project overview
- personal portfolio backend documentation
- project handoff / internal sharing

---

## Author

**DAPTrax**

Built as a lightweight and secure finance-tracking backend project focused on practical architecture and maintainable implementation.
