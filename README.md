# VSPP ADO Sync Platform ![status](https://img.shields.io/badge/version-v0.0.1-ED2831?style=flat&logo=github)

Synchronises **MediaKind** Feature Requests with **TechMahindra** EPICs, provides a real-time dashboard, and automates progress updates.

## Tech Stack
* **Backend** — Python 3.11, FastAPI, Motor (MongoDB), Uvicorn
* **Frontend** — React 18 + Vite, Tailwind CSS, shadcn/ui
* **Database** — MongoDB (JSON-first)
* **Deployment** — Docker Compose

## Local dev (first run)

```bash
git clone https://github.com/aviaki/vspp-ado-sync-platform.git
cd vspp-ado-sync-platform
cp .env.example .env   # fill in JWT_SECRET, ADO PATs, SMTP creds, …
docker compose up --build
```

* UI → http://localhost  
* API docs → http://localhost/api/docs  
* Mongo shell → `docker exec -it vspp-mongo mongosh`

> **Branding note** – UI colours follow TechMahindra’s Imperial Red **#ED2831** and Dark Grey **#6D6C71**.
