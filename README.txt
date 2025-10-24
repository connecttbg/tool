Tool Inventory – Full Flask App (Render-ready)
====================================================
Start (lokalnie):
1) python -m venv .venv
2) .venv/Scripts/activate   (Windows)  lub  source .venv/bin/activate (macOS/Linux)
3) pip install -r requirements.txt
4) set ADMIN_PASSWORD=admin   (PowerShell: $env:ADMIN_PASSWORD="admin")
5) python app.py  -> http://127.0.0.1:5000

Render.com:
- Build: pip install -r requirements.txt
- Start: gunicorn app:app
- Env: ADMIN_PASSWORD, SECRET_KEY, (opcjonalnie) UPLOAD_DIR=/var/data/uploads
- Dodaj Persistent Disk i ustaw mount na /var/data, by zdjęcia były trwałe.
