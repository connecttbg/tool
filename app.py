"""
Tool Inventory – Flask MVP (fixed templates loader)
"""

import os
import qrcode
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename

from flask import (
    Flask, request, redirect, url_for, render_template,
    send_from_directory, session, jsonify, flash
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from jinja2 import DictLoader

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "inventory.db"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{DB_PATH}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
)

db = SQLAlchemy(app)

class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(80), default="")
    serial_no = db.Column(db.String(120), default="")
    photo_path = db.Column(db.String(255), default="")
    holder = db.Column(db.String(120), default="")
    checkout_date = db.Column(db.String(10), default="")
    qr_path = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    person = db.Column(db.String(120), default="")
    when = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, default="")

with app.app_context():
    db.create_all()

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def require_login(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)
    return wrapper

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/login', methods=['GET', 'POST'])
def login():
    err = None
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        admin_pwd = os.environ.get('ADMIN_PASSWORD', 'admin')
        if pwd == admin_pwd:
            session['logged_in'] = True
            return redirect(request.args.get('next') or url_for('index'))
        err = 'Nieprawidłowe hasło.'
    return render_template('login.html', err=err)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@require_login
def index():
    q = request.args.get('q', '').strip()
    cat = request.args.get('cat', '').strip()
    holder = request.args.get('holder', '').strip()

    query = Tool.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Tool.name.ilike(like), Tool.description.ilike(like), Tool.serial_no.ilike(like))
        )
    if cat:
        query = query.filter_by(category=cat)
    if holder:
        query = query.filter_by(holder=holder)

    tools = query.order_by(Tool.created_at.desc()).all()
    cats = [c[0] for c in db.session.query(Tool.category).distinct().all() if c[0]]
    holders = [h[0] for h in db.session.query(Tool.holder).distinct().all() if h[0]]
    return render_template('index.html', tools=tools, cats=cats, holders=holders, q=q, cat=cat, holder=holder)

@app.route('/tool/new', methods=['GET', 'POST'])
@require_login
def tool_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        serial_no = request.form.get('serial_no', '').strip()

        photo_file = request.files.get('photo')
        photo_path = ""
        if photo_file and allowed_file(photo_file.filename):
            fname = secure_filename(photo_file.filename)
            ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            fname = f"{ts}_{fname}"
            save_path = UPLOAD_DIR / fname
            photo_file.save(save_path)
            photo_path = f"/uploads/{fname}"

        tool = Tool(name=name, description=description, category=category, serial_no=serial_no, photo_path=photo_path)
        db.session.add(tool)
        db.session.commit()

        qr_url = url_for('tool_detail', tool_id=tool.id, _external=True)
        img = qrcode.make(qr_url)
        qr_fname = f"qr_tool_{tool.id}.png"
        img.save(UPLOAD_DIR / qr_fname)
        tool.qr_path = f"/uploads/{qr_fname}"
        db.session.commit()

        flash('Narzędzie dodane.', 'success')
        return redirect(url_for('tool_detail', tool_id=tool.id))

    return render_template('tool_new.html')

@app.route('/tool/<int:tool_id>')
@require_login
def tool_detail(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    events = Event.query.filter_by(tool_id=tool.id).order_by(Event.when.desc()).all()
    return render_template('tool_detail.html', tool=tool, events=events)

@app.route('/tool/<int:tool_id>/edit', methods=['GET', 'POST'])
@require_login
def tool_edit(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    if request.method == 'POST':
        tool.name = request.form.get('name', tool.name)
        tool.description = request.form.get('description', tool.description)
        tool.category = request.form.get('category', tool.category)
        tool.serial_no = request.form.get('serial_no', tool.serial_no)

        photo_file = request.files.get('photo')
        if photo_file and allowed_file(photo_file.filename):
            fname = secure_filename(photo_file.filename)
            ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            fname = f"{ts}_{fname}"
            save_path = UPLOAD_DIR / fname
            photo_file.save(save_path)
            tool.photo_path = f"/uploads/{fname}"

        db.session.add(Event(tool_id=tool.id, type='edit', note='Edycja karty'))
        db.session.commit()
        flash('Zapisano zmiany.', 'success')
        return redirect(url_for('tool_detail', tool_id=tool.id))

    return render_template('tool_edit.html', tool=tool)

@app.route('/tool/<int:tool_id>/checkout', methods=['POST'])
@require_login
def tool_checkout(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    person = request.form.get('person', '').strip()
    date = request.form.get('date', '').strip() or datetime.utcnow().strftime('%Y-%m-%d')
    tool.holder = person
    tool.checkout_date = date
    db.session.add(Event(tool_id=tool.id, type='checkout', person=person, note=f"Wydano {date}"))
    db.session.commit()
    flash('Wydano narzędzie.', 'success')
    return redirect(url_for('tool_detail', tool_id=tool.id))

@app.route('/tool/<int:tool_id>/return', methods=['POST'])
@require_login
def tool_return(tool_id):
    tool = Tool.query.get_or_404(tool_id)
    person = tool.holder
    tool.holder = ""
    tool.checkout_date = ""
    db.session.add(Event(tool_id=tool.id, type='return', person=person, note="Zwrot"))
    db.session.commit()
    flash('Przyjęto zwrot.', 'success')
    return redirect(url_for('tool_detail', tool_id=tool.id))

@app.route('/api/tools')
@require_login
def api_tools():
    tools = Tool.query.order_by(Tool.created_at.desc()).all()
    return jsonify([
        {
            'id': t.id,
            'name': t.name,
            'description': t.description,
            'category': t.category,
            'serial_no': t.serial_no,
            'photo_url': t.photo_path,
            'holder': t.holder,
            'checkout_date': t.checkout_date,
            'qr_url': t.qr_path,
            'detail_url': url_for('tool_detail', tool_id=t.id, _external=True)
        } for t in tools
    ])

# ---- Templates via DictLoader ----
TPL_BASE = r"""<!doctype html>
<html lang="pl">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Inwentaryzacja narzędzi</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <a class="navbar-brand" href="{{ url_for('index') }}">Narzędzia</a>
      <div class="d-flex gap-2">
        <a class="btn btn-sm btn-outline-light" href="{{ url_for('tool_new') }}">+ Dodaj</a>
        <a class="btn btn-sm btn-outline-warning" href="{{ url_for('logout') }}">Wyloguj</a>
      </div>
    </div>
  </nav>
  <main class="container py-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="alert alert-{{ 'warning' if cat=='message' else cat }}">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  </body>
</html>"""

TPL_LOGIN = r"""{% extends 'base.html' %}
{% block content %}
  <div class="container py-5" style="max-width:480px;">
    <div class="card shadow-sm">
      <div class="card-body">
        <h1 class="h4 mb-3">Logowanie</h1>
        {% if err %}<div class="alert alert-danger">{{ err }}</div>{% endif %}
        <form method="post">
          <div class="mb-3">
            <label class="form-label">Hasło administratora</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          <button class="btn btn-primary w-100">Zaloguj</button>
        </form>
      </div>
    </div>
  </div>
{% endblock %}"""

TPL_INDEX = r"""{% extends 'base.html' %}
{% block content %}
  <form class="row gy-2 gx-2 align-items-end mb-3">
    <div class="col-12 col-md-5">
      <label class="form-label">Szukaj</label>
      <input class="form-control" name="q" value="{{ q }}" placeholder="nazwa / opis / numer seryjny">
    </div>
    <div class="col-6 col-md-3">
      <label class="form-label">Kategoria</label>
      <select class="form-select" name="cat">
        <option value="">(wszystkie)</option>
        {% for c in cats %}
          <option value="{{ c }}" {% if c==cat %}selected{% endif %}>{{ c }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-6 col-md-2">
      <label class="form-label">Posiadacz</label>
      <select class="form-select" name="holder">
        <option value="">(wszyscy)</option>
        {% for h in holders %}
          <option value="{{ h }}" {% if h==holder %}selected{% endif %}>{{ h }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-12 col-md-2">
      <button class="btn btn-primary w-100">Filtruj</button>
    </div>
  </form>

  <div class="row g-3">
    {% for t in tools %}
      <div class="col-12 col-md-6 col-lg-4">
        <div class="card h-100 shadow-sm">
          {% if t.photo_path %}
            <img src="{{ t.photo_path }}" class="card-img-top" alt="{{ t.name }}" style="object-fit:cover; height:200px;">
          {% endif %}
          <div class="card-body">
            <h5 class="card-title">{{ t.name }}</h5>
            <p class="card-text small text-muted mb-2">{{ t.category }}{% if t.serial_no %} • SN: {{ t.serial_no }}{% endif %}</p>
            {% if t.holder %}
              <span class="badge bg-danger">U kogo: {{ t.holder }} od {{ t.checkout_date }}</span>
            {% else %}
              <span class="badge bg-success">Dostępne</span>
            {% endif %}
          </div>
          <div class="card-footer d-flex gap-2">
            <a class="btn btn-sm btn-outline-primary" href="{{ url_for('tool_detail', tool_id=t.id) }}">Otwórz</a>
          </div>
        </div>
      </div>
    {% else %}
      <div class="col-12"><div class="alert alert-info">Brak wyników.</div></div>
    {% endfor %}
  </div>
{% endblock %}"""

TPL_TOOL_NEW = r"""{% extends 'base.html' %}
{% block content %}
  <h1 class="h4 mb-3">Dodaj narzędzie</h1>
  <form method="post" enctype="multipart/form-data" class="row g-3">
    <div class="col-12">
      <label class="form-label">Nazwa*</label>
      <input class="form-control" name="name" required>
    </div>
    <div class="col-12">
      <label class="form-label">Opis</label>
      <textarea class="form-control" name="description" rows="3"></textarea>
    </div>
    <div class="col-md-6">
      <label class="form-label">Kategoria</label>
      <input class="form-control" name="category" placeholder="np. elektronarzędzia">
    </div>
    <div class="col-md-6">
      <label class="form-label">Numer seryjny</label>
      <input class="form-control" name="serial_no">
    </div>
    <div class="col-12">
      <label class="form-label">Zdjęcie</label>
      <input class="form-control" type="file" name="photo" accept="image/*">
    </div>
    <div class="col-12">
      <button class="btn btn-primary">Zapisz</button>
      <a class="btn btn-light" href="{{ url_for('index') }}">Anuluj</a>
    </div>
  </form>
{% endblock %}"""

TPL_TOOL_EDIT = r"""{% extends 'base.html' %}
{% block content %}
  <h1 class="h4 mb-3">Edytuj: {{ tool.name }}</h1>
  <form method="post" enctype="multipart/form-data" class="row g-3">
    <div class="col-12">
      <label class="form-label">Nazwa*</label>
      <input class="form-control" name="name" value="{{ tool.name }}" required>
    </div>
    <div class="col-12">
      <label class="form-label">Opis</label>
      <textarea class="form-control" name="description" rows="3">{{ tool.description }}</textarea>
    </div>
    <div class="col-md-6">
      <label class="form-label">Kategoria</label>
      <input class="form-control" name="category" value="{{ tool.category }}">
    </div>
    <div class="col-md-6">
      <label class="form-label">Numer seryjny</label>
      <input class="form-control" name="serial_no" value="{{ tool.serial_no }}">
    </div>
    <div class="col-12">
      <label class="form-label">Zdjęcie (opcjonalnie)</label>
      <input class="form-control" type="file" name="photo" accept="image/*">
    </div>
    <div class="col-12">
      <button class="btn btn-primary">Zapisz zmiany</button>
      <a class="btn btn-light" href="{{ url_for('tool_detail', tool_id=tool.id) }}">Wróć</a>
    </div>
  </form>
{% endblock %}"""

TPL_TOOL_DETAIL = r"""{% extends 'base.html' %}
{% block content %}
  <div class="row g-3">
    <div class="col-lg-8">
      <div class="card shadow-sm">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h1 class="h4 mb-0">{{ tool.name }}</h1>
            <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('tool_edit', tool_id=tool.id) }}">Edytuj</a>
          </div>
          <p class="text-muted small mb-2">Kategoria: {{ tool.category or '—' }} • SN: {{ tool.serial_no or '—' }}</p>
          {% if tool.photo_path %}
            <img src="{{ tool.photo_path }}" class="rounded mb-3" style="max-height:320px; object-fit:cover;">
          {% endif %}
          <p>{{ tool.description or '' }}</p>

          {% if tool.holder %}
            <div class="alert alert-warning d-flex justify-content-between align-items-center">
              <div><strong>Wydane:</strong> {{ tool.holder }} od {{ tool.checkout_date }}</div>
              <form method="post" action="{{ url_for('tool_return', tool_id=tool.id) }}">
                <button class="btn btn-sm btn-success">Przyjmij zwrot</button>
              </form>
            </div>
          {% else %}
            <form class="row g-2" method="post" action="{{ url_for('tool_checkout', tool_id=tool.id) }}">
              <div class="col-md-5">
                <label class="form-label">Kto pobiera</label>
                <input class="form-control" name="person" placeholder="np. Jan Kowalski" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Data pobrania</label>
                <input class="form-control" type="date" name="date" value="{{ now().strftime('%Y-%m-%d') if now else '' }}">
              </div>
              <div class="col-md-3 align-self-end">
                <button class="btn btn-primary w-100">Wydaj</button>
              </div>
            </form>
          {% endif %}
        </div>
      </div>
    </div>

    <div class="col-lg-4">
      <div class="card shadow-sm mb-3">
        <div class="card-body">
          <h6 class="mb-2">QR – karta narzędzia</h6>
          {% if tool.qr_path %}
            <img src="{{ tool.qr_path }}" class="img-fluid" alt="QR">
            <p class="small text-muted mt-2">Zeskanuj, by otworzyć tę stronę.</p>
          {% else %}
            <p class="text-muted">Brak kodu QR.</p>
          {% endif %}
        </div>
      </div>
      <div class="card shadow-sm">
        <div class="card-body">
          <h6 class="mb-2">Historia</h6>
          {% if events %}
            <ul class="list-group list-group-flush">
              {% for e in events %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                  <span>
                    {% if e.type=='checkout' %}Wydanie{% elif e.type=='return' %}Zwrot{% else %}Edycja{% endif %}
                    <span class="text-muted">{{ e.person or '' }}</span>
                  </span>
                  <span class="small text-muted">{{ e.when.strftime('%Y-%m-%d %H:%M') }}</span>
                </li>
              {% endfor %}
            </ul>
          {% else %}
            <p class="text-muted">Brak zdarzeń.</p>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
{% endblock %}"""

# Register templates in a DictLoader and also keep 'now' helper
app.jinja_loader = DictLoader({
    'base.html': TPL_BASE,
    'login.html': TPL_LOGIN,
    'index.html': TPL_INDEX,
    'tool_new.html': TPL_TOOL_NEW,
    'tool_edit.html': TPL_TOOL_EDIT,
    'tool_detail.html': TPL_TOOL_DETAIL,
})

@app.context_processor
def inject_now():
    return dict(now=datetime.utcnow)

REQ_TXT = "flask>=3.0\nflask_sqlalchemy>=3.1\nqrcode[pil]>=7.4\nWerkzeug>=3.0\nJinja2>=3.1\n"

@app.route('/requirements.txt')
def requirements_txt():
    return REQ_TXT, 200, {"Content-Type": "text/plain; charset=utf-8"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
