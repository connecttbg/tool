Tool Inventory – Flask MVP (fixed)
====================================

Ten zestaw naprawia błąd `jinja2.exceptions.TemplateNotFound` przez użycie `DictLoader`.
Instrukcja (Windows PowerShell):

1) python -m venv .venv
2) .venv\Scripts\Activate.ps1
3) pip install -r requirements.txt
4) $env:ADMIN_PASSWORD="TwojeMocneHaslo"
5) python app.py
6) Otwórz http://127.0.0.1:5000

Logowanie: wpisz dokładnie to hasło, które ustawisz w zmiennej ADMIN_PASSWORD.
