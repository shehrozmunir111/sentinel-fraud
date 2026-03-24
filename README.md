# 🛡️ SentinelFraud

[![FastAPI](https://img.shields.io/badge/FastAPI-v0.111.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-v16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-v7.2-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SentinelFraud** is a high-performance, real-time fraud detection engine designed for modern fintech applications. It leverages asynchronous processing and Machine Learning to detect fraudulent transactions with sub-100ms latency.

---

## 📸 System Showcase

![SentinelFraud Dashboard/API](assets/endpoints.png)

---

## ✨ Features

- 🏎️ **Ultra-fast Scoring:** AsyncIO-powered FastAPI backend optimized for high concurrency.
- 🧠 **ML Intelligence:** Pre-trained Random Forest model for behavioral fraud detection.
- ⚙️ **Dynamic Rule Engine:** Real-time velocity checks and amount limits (configurable via API).
- 📡 **Real-time Alerts:** Fraud notifications delivered instantly via WebSockets.
- 🏗️ **Robust Architecture:** PostgreSQL for persistence, Redis for caching and velocity tracking.
- 🔐 **Enterprise Security:** JWT-based authentication with role-based access control (RBAC).

---

## 🏗️ Technical Stack

- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async)
- **Cache & Messaging:** [Redis](https://redis.io/)
- **ML Engine:** [Scikit-learn](https://scikit-learn.org/), [Pandas](https://pandas.pydata.org/)
- **Authentication:** [Jose JWT](https://python-jose.readthedocs.io/), [Bcrypt](https://pypi.org/project/bcrypt/)
- **Logging:** [Structlog](https://www.structlog.org/)

---

## 🚀 Quick Setup

### 📦 Docker Support (Recommended)
SentinelFraud is designed to run seamlessly in Docker.

```bash
cp .env.example .env
docker-compose -f docker/docker-compose.yml up -d
```

### 💻 Local Development
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/sentinel-fraud.git
   cd sentinel-fraud
   ```

2. **Initialize Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Database Configuration:**
   Ensure PostgreSQL is running and update `DATABASE_URI` in `.env`.

4. **Launch Application:**
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 📜 API Documentation

Once the server is running, explore the interactive API through:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) 🚀
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc) 📖
- **Root Info:** [http://localhost:8000/](http://localhost:8000/) 🏠

---

## 🧪 Testing

The system is backed by a comprehensive test suite using **Pytest**.

```bash
# Set up test database 'sentinelfraud' in PostgreSQL
python -m pytest tests/ -v
```

---

## 📁 Project Overview

```text
├── app/                  # Enterprise Backend
│   ├── api/              # Restful Endpoints (v1)
│   ├── core/             # Config, Security, Logging, Middleware
│   ├── models/           # DB Schemas (SQLAlchemy)
│   ├── schemas/          # Data Validation (Pydantic)
│   └── services/         # Rule Engine & Business Logic
├── ml/                   # ML Training & Prediction
├── tests/                # Integration & Unit Tests
└── docker/               # Container Orchestration
```

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.
