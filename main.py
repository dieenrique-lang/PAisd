from zoneinfo import ZoneInfo
from datetime import datetime
from html import escape
from io import BytesIO
import os

import bcrypt
import psycopg
from fastapi import Cookie, FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from itsdangerous import BadSignature, URLSafeSerializer
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esto")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

serializer = URLSafeSerializer(SECRET_KEY, salt="admin-session")


# ---------- Infraestructura ----------
def ahora_chile():
    return datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)
    
def conectar():
    return psycopg.connect(DATABASE_URL)


def crear_tablas():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS departamentos (
                    id SERIAL PRIMARY KEY,
                    torre TEXT,
                    numero TEXT NOT NULL,
                    UNIQUE(torre, numero)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS residentes (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    telefono TEXT,
                    email TEXT,
                    tipo TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehiculos (
                    id SERIAL PRIMARY KEY,
                    patente TEXT NOT NULL,
                    marca TEXT,
                    modelo TEXT,
                    color TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS visitas (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    rut TEXT,
                    patente TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id),
                    autorizado_por TEXT,
                    observacion TEXT,
                    hora_ingreso TIMESTAMP DEFAULT NOW(),
                    hora_salida TIMESTAMP
                )
                """
            )
            cursor.execute("ALTER TABLE visitas ADD COLUMN IF NOT EXISTS patente TEXT")
        conn.commit()


# ---------- Auth admin ----------
def crear_token_admin():
    return serializer.dumps({"admin": True})


def require_admin(token: str | None):
    if not token:
        return False
    try:
        data = serializer.loads(token)
        return data.get("admin") is True
    except BadSignature:
        return False


def verificar_password_admin(password: str):
    if not ADMIN_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))


# ---------- Helpers UI ----------
def h(value):
    return escape(str(value or ""))


def format_depto(torre, numero):
    if torre and numero:
        return f"{h(torre)}-{h(numero)}"
    return h(torre or numero)


def render_delete_action(es_admin: bool, href: str, confirm_text: str):
    if not es_admin:
        return "<span class='muted'>Solo admin</span>"
    return (
        f"<a class='btn red' href='{h(href)}' "
        f"onclick=\"return confirm('{h(confirm_text)}')\">Eliminar</a>"
    )


def layout(titulo: str, contenido: str):
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{h(titulo)}</title>
        <style>
            :root {{
                --bg:#eef2ff;
                --surface:#ffffff;
                --text:#0f172a;
                --muted:#64748b;
                --primary:#1d4ed8;
                --primary-dark:#1e3a8a;
                --danger:#dc2626;
                --success:#16a34a;
                --border:#dbe2ea;
                --shadow:0 10px 28px rgba(15,23,42,.08);
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                background: radial-gradient(circle at top left,#dbeafe,var(--bg));
                margin: 0;
                padding: 32px 18px;
                color: var(--text);
            }}
            .wrap {{ max-width: 1150px; margin: 0 auto; }}
            .hero {{
                background: linear-gradient(125deg,var(--primary),var(--primary-dark));
                color: white;
                padding: 28px;
                border-radius: 18px;
                margin-bottom: 20px;
                box-shadow: var(--shadow);
            }}
            .hero h1 {{ margin: 0 0 6px; }}
            .hero p {{ margin: 0; opacity: .92; }}
            .card {{
                background: var(--surface);
                border: 1px solid var(--border);
                padding: 22px;
                border-radius: 16px;
                box-shadow: var(--shadow);
                margin-bottom: 18px;
            }}
            .actions {{ display:flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
            form {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap: 10px; }}
            form .full {{ grid-column: 1/-1; }}
            input, select, textarea {{
                width: 100%;
                padding: 10px 12px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                outline: none;
                font-size: .95rem;
            }}
            input:focus, select:focus, textarea:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,.15); }}
            button, .btn {{
                display:inline-flex;
                align-items:center;
                justify-content:center;
                background: var(--primary);
                color:#fff;
                border:none;
                border-radius: 10px;
                text-decoration:none;
                padding: 9px 14px;
                font-weight: 600;
                cursor:pointer;
            }}
            .btn.dark {{ background:#0f172a; }}
            .btn.red {{ background: var(--danger); }}
            .btn.green {{ background: var(--success); }}
            .muted {{ color: var(--muted); font-weight: 600; }}
            table {{ width:100%; border-collapse: separate; border-spacing: 0; overflow:hidden; border: 1px solid var(--border); border-radius: 14px; }}
            th {{ background: #eff6ff; color: #1e3a8a; text-align:left; padding: 11px; font-size:.92rem; }}
            td {{ background:#fff; padding: 10px 11px; border-top: 1px solid var(--border); }}
            .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 14px; }}
            .stat {{ font-size: 2rem; font-weight: 800; color: var(--primary); }}
        </style>
    </head>
    <body>
        <div class="wrap">{contenido}</div>
    </body>
    </html>
    """


@app.on_event("startup")
def startup_event():
    try:
        crear_tablas()
    except Exception as exc:
        print(f"[startup] No se pudieron crear/verificar tablas: {exc}")


@app.get("/", response_class=HTMLResponse)
def inicio():
    contenido = """
    <div class="hero">
        <h1>CondoControl</h1>
        <p>Sistema de control de residentes, vehículos y visitas para condominios.</p>
    </div>
    <div class="card">
        <h2>Menú principal</h2>
        <div class="actions">
            <a class="btn" href="/residentes">Residentes</a>
            <a class="btn" href="/vehiculos">Vehículos</a>
            <a class="btn" href="/visitas">Control de visitas</a>
            <a class="btn" href="/dashboard-condominio">Dashboard</a>
            <a class="btn dark" href="/admin/login">Acceso administrador</a>
        </div>
    </div>
    """
    return layout("CondoControl", contenido)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form():
    contenido = """
    <div class="card" style="max-width:460px;margin:auto;">
        <h2>Acceso administrador</h2>
        <form action="/admin/login" method="post">
            <input name="username" placeholder="Usuario" required>
            <input name="password" type="password" placeholder="Contraseña" required>
            <button class="full" type="submit">Entrar</button>
        </form>
        <div class="actions"><a class="btn dark" href="/">Volver</a></div>
    </div>
    """
    return layout("Login admin", contenido)


@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if username != ADMIN_USERNAME or not verificar_password_admin(password):
        return HTMLResponse("<h3>Credenciales incorrectas</h3><a href='/admin/login'>Volver</a>", status_code=401)

    response = RedirectResponse(url="/residentes", status_code=303)
    response.set_cookie(key="admin_session", value=crear_token_admin(), httponly=True, samesite="lax", secure=False)
    return response


@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_session")
    return response


def obtener_o_crear_departamento(cursor, torre, numero):
    cursor.execute(
        """
        SELECT id FROM departamentos
        WHERE COALESCE(torre, '') = COALESCE(%s, '') AND numero = %s
        """,
        (torre, numero),
    )
    dep = cursor.fetchone()
    if dep:
        return dep[0]

    cursor.execute(
        """
        INSERT INTO departamentos (torre, numero)
        VALUES (%s, %s)
        RETURNING id
        """,
        (torre, numero),
    )
    return cursor.fetchone()[0]


@app.get("/residentes", response_class=HTMLResponse)
def residentes(admin_session: str | None = Cookie(default=None)):
    es_admin = require_admin(admin_session)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT r.id, r.nombre, r.telefono, r.email, r.tipo, d.torre, d.numero
                FROM residentes r
                LEFT JOIN departamentos d ON r.departamento_id = d.id
                ORDER BY r.id DESC
                """
            )
            data = cursor.fetchall()

    filas = "".join(
        f"""
        <tr>
            <td>{h(r[1])}</td>
            <td>{format_depto(r[5], r[6])}</td>
            <td>{h(r[2])}</td>
            <td>{h(r[3])}</td>
            <td>{h(r[4])}</td>
            <td>{render_delete_action(es_admin, f'/eliminar-residente/{r[0]}', '¿Eliminar residente?')}</td>
        </tr>
        """
        for r in data
    )

    logout = '<a class="btn dark" href="/admin/logout">Cerrar sesión admin</a>' if es_admin else ""

    contenido = f"""
    <div class="hero"><h1>Residentes</h1><p>Registro de residentes por departamento.</p></div>
    <div class="card">
        <h2>Agregar residente</h2>
        <form action="/guardar-residente" method="post">
            <input name="nombre" placeholder="Nombre residente" required>
            <input name="telefono" placeholder="Teléfono">
            <input name="email" placeholder="Email">
            <select name="tipo">
                <option value="Propietario">Propietario</option>
                <option value="Arrendatario">Arrendatario</option>
                <option value="Residente">Residente</option>
            </select>
            <input name="torre" placeholder="Torre / Block">
            <input name="numero" placeholder="Departamento" required>
            <button class="full" type="submit">Guardar residente</button>
        </form>
    </div>
    <div class="card">
        <h2>Listado</h2>
        <table>
            <tr><th>Nombre</th><th>Depto</th><th>Teléfono</th><th>Email</th><th>Tipo</th><th>Acción</th></tr>
            {filas}
        </table>
    </div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/dashboard-condominio">Dashboard</a>
        {logout}
    </div>
    """
    return layout("Residentes", contenido)


@app.post("/guardar-residente")
def guardar_residente(
    nombre: str = Form(...),
    telefono: str = Form(""),
    email: str = Form(""),
    tipo: str = Form("Residente"),
    torre: str = Form(""),
    numero: str = Form(...),
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, torre, numero)
            cursor.execute(
                """
                INSERT INTO residentes (nombre, telefono, email, tipo, departamento_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (nombre, telefono, email, tipo, dep_id),
            )
        conn.commit()
    return RedirectResponse(url="/residentes", status_code=303)


@app.get("/eliminar-residente/{residente_id}")
def eliminar_residente(residente_id: int, admin_session: str | None = Cookie(default=None)):
    if not require_admin(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM residentes WHERE id = %s", (residente_id,))
        conn.commit()
    return RedirectResponse(url="/residentes", status_code=303)


@app.get("/vehiculos", response_class=HTMLResponse)
def vehiculos(admin_session: str | None = Cookie(default=None)):
    es_admin = require_admin(admin_session)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.id, v.patente, v.marca, v.modelo, v.color, d.torre, d.numero
                FROM vehiculos v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                ORDER BY v.id DESC
                """
            )
            data = cursor.fetchall()

    filas = "".join(
        f"""
        <tr>
            <td>{h(v[1])}</td><td>{h(v[2])}</td><td>{h(v[3])}</td><td>{h(v[4])}</td><td>{format_depto(v[5], v[6])}</td>
            <td>{render_delete_action(es_admin, f'/eliminar-vehiculo/{v[0]}', '¿Eliminar vehículo?')}</td>
        </tr>
        """
        for v in data
    )

    contenido = f"""
    <div class="hero"><h1>Vehículos</h1><p>Registro de autos por departamento.</p></div>
    <div class="card">
        <h2>Agregar vehículo</h2>
        <form action="/guardar-vehiculo" method="post">
            <input name="patente" placeholder="Patente" required>
            <input name="marca" placeholder="Marca">
            <input name="modelo" placeholder="Modelo">
            <input name="color" placeholder="Color">
            <input name="torre" placeholder="Torre / Block">
            <input name="numero" placeholder="Departamento" required>
            <button class="full" type="submit">Guardar vehículo</button>
        </form>
    </div>
    <div class="card">
        <h2>Listado vehículos</h2>
        <table>
            <tr><th>Patente</th><th>Marca</th><th>Modelo</th><th>Color</th><th>Depto</th><th>Acción</th></tr>
            {filas}
        </table>
    </div>
    <div class="actions"><a class="btn" href="/">Inicio</a></div>
    """
    return layout("Vehículos", contenido)


@app.post("/guardar-vehiculo")
def guardar_vehiculo(
    patente: str = Form(...),
    marca: str = Form(""),
    modelo: str = Form(""),
    color: str = Form(""),
    torre: str = Form(""),
    numero: str = Form(...),
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, torre, numero)
            cursor.execute(
                """
                INSERT INTO vehiculos (patente, marca, modelo, color, departamento_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (patente.upper(), marca, modelo, color, dep_id),
            )
        conn.commit()
    return RedirectResponse(url="/vehiculos", status_code=303)


@app.get("/eliminar-vehiculo/{vehiculo_id}")
def eliminar_vehiculo(vehiculo_id: int, admin_session: str | None = Cookie(default=None)):
    if not require_admin(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM vehiculos WHERE id = %s", (vehiculo_id,))
        conn.commit()
    return RedirectResponse(url="/vehiculos", status_code=303)


@app.get("/visitas", response_class=HTMLResponse)
def visitas(q: str = Query(default=""), solo_dentro: int = Query(default=0)):
    with conectar() as conn:
        with conn.cursor() as cursor:
            where_parts = []
            params = []
            if q:
                like = f"%{q}%"
                where_parts.append(
                    """
                    (
                        v.nombre ILIKE %s OR
                        v.rut ILIKE %s OR
                        v.patente ILIKE %s OR
                        COALESCE(d.torre, '') ILIKE %s OR
                        d.numero ILIKE %s OR
                        (COALESCE(d.torre, '') || '-' || d.numero) ILIKE %s
                    )
                    """
                )
                params.extend([like, like, like, like, like, like])
            if solo_dentro:
                where_parts.append("v.hora_salida IS NULL")

            where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            cursor.execute(
                """
                SELECT v.id, v.nombre, v.rut, v.patente, d.torre, d.numero, v.autorizado_por,
                       v.observacion, v.hora_ingreso, v.hora_salida
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                """
                + where_sql
                + """
                ORDER BY v.id DESC
                LIMIT 100
                """,
                params,
            )
            data = cursor.fetchall()

    filas = ""
    for v in data:
        estado = "Dentro" if v[9] is None else "Salió"
        salida = f"<a class='btn green' href='/salida-visita/{v[0]}'>Marcar salida</a>" if v[9] is None else h(v[9])
        filas += f"""
        <tr>
            <td>{h(v[1])}</td>
            <td>{h(v[2])}</td>
            <td>{h(v[3])}</td>
            <td>{format_depto(v[4], v[5])}</td>
            <td>{h(v[6])}</td>
            <td>{h(v[8])}</td>
            <td>{estado}</td>
            <td>{salida}</td>
        </tr>
        """

    checked = "checked" if solo_dentro else ""
    contenido = f"""
    <div class="hero"><h1>Control de visitas</h1><p>Registro de ingreso y salida para conserjería.</p></div>
    <div class="card">
        <h2>Registrar ingreso</h2>
        <form action="/guardar-visita" method="post">
            <input name="nombre" placeholder="Nombre visita" required>
            <input name="rut" placeholder="RUT / Documento">
            <input name="patente" placeholder="Patente vehículo (opcional)">
            <input name="torre" placeholder="Torre / Block">
            <input name="numero" placeholder="Departamento que visita" required>
            <input name="autorizado_por" placeholder="Autorizado por">
            <textarea class="full" name="observacion" placeholder="Observación"></textarea>
            <button class="full" type="submit">Registrar ingreso</button>
        </form>
    </div>
    <div class="card">
        <h2>Buscar y filtrar</h2>
        <form action="/visitas" method="get">
            <input name="q" value="{h(q)}" placeholder="Buscar por nombre, RUT, patente o depto">
            <label style="display:flex;align-items:center;gap:8px;padding:8px 4px;">
                <input type="checkbox" name="solo_dentro" value="1" {checked} style="width:auto;">
                Solo visitas dentro del condominio
            </label>
            <button type="submit">Aplicar filtros</button>
            <a class="btn dark" href="/visitas">Limpiar</a>
        </form>
    </div>
    <div class="card">
        <h2>Últimas visitas</h2>
        <table>
            <tr><th>Visita</th><th>RUT</th><th>Patente</th><th>Depto</th><th>Autoriza</th><th>Ingreso</th><th>Estado</th><th>Salida</th></tr>
            {filas}
        </table>
    </div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/exportar/visitas">Exportar visitas</a>
    </div>
    """
    return layout("Visitas", contenido)


@app.post("/guardar-visita")
def guardar_visita(
    nombre: str = Form(...),
    rut: str = Form(""),
    patente: str = Form(""),
    torre: str = Form(""),
    numero: str = Form(...),
    autorizado_por: str = Form(""),
    observacion: str = Form(""),
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, torre, numero)
            cursor.execute(
                """
                INSERT INTO visitas (nombre, rut, patente, departamento_id, autorizado_por, observacion, hora_ingreso)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
             (nombre, rut, patente.upper(), dep_id, autorizado_por, observacion, ahora_chile())
        conn.commit()
    return RedirectResponse(url="/visitas", status_code=303)


@app.get("/salida-visita/{visita_id}")
def salida_visita(visita_id: int):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE visitas
                SET hora_salida = %s
                WHERE id = %s AND hora_salida IS NULL
                """,
                (ahora_chile(), visita_id)
        conn.commit()
    return RedirectResponse(url="/visitas", status_code=303)


@app.get("/dashboard-condominio", response_class=HTMLResponse)
def dashboard_condominio():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM residentes")
            total_residentes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM vehiculos")
            total_vehiculos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM visitas WHERE DATE(hora_ingreso) = CURRENT_DATE")
            visitas_hoy = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM visitas WHERE hora_salida IS NULL")
            visitas_dentro = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT d.torre, d.numero, COUNT(v.id) AS total
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                GROUP BY d.torre, d.numero
                ORDER BY total DESC
                LIMIT 5
                """
            )
            top_deptos = cursor.fetchall()

    top_html = "".join(f"<li>{format_depto(d[0], d[1])}: {d[2]} visitas</li>" for d in top_deptos) or "<li>No hay datos</li>"
    ahora = ahora_chile().strftime("%Y-%m-%d %H:%M")

    contenido = f"""
    <div class="hero"><h1>Dashboard Condominio</h1><p>Resumen operativo para administración y comité.</p></div>
    <div class="grid">
        <div class="card"><h3>Residentes</h3><div class="stat">{total_residentes}</div></div>
        <div class="card"><h3>Vehículos</h3><div class="stat">{total_vehiculos}</div></div>
        <div class="card"><h3>Visitas hoy</h3><div class="stat">{visitas_hoy}</div></div>
        <div class="card"><h3>Visitas dentro</h3><div class="stat">{visitas_dentro}</div></div>
    </div>
    <div class="card"><h2>Top departamentos con más visitas</h2><ul>{top_html}</ul><p class="muted">Actualizado: {h(ahora)}</p></div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/visitas">Control visitas</a>
        <a class="btn" href="/exportar/visitas">Exportar visitas</a>
    </div>
    """
    return layout("Dashboard Condominio", contenido)


@app.get("/exportar/visitas")
def exportar_visitas():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.id, v.nombre, v.rut, v.patente, d.torre, d.numero, v.autorizado_por,
                       v.observacion, v.hora_ingreso, v.hora_salida
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                ORDER BY v.id DESC
                """
            )
            visitas = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Visitas"

    headers = [
        "ID",
        "Nombre visita",
        "RUT",
        "Patente",
        "Torre",
        "Departamento",
        "Autorizado por",
        "Observación",
        "Hora ingreso",
        "Hora salida",
    ]
    ws.append(headers)

    fill = PatternFill(fill_type="solid", fgColor="2563EB")
    font = Font(color="FFFFFF", bold=True)
    align = Alignment(horizontal="center")

    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align

    for visita in visitas:
        ws.append(list(visita))

    for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
        ws.column_dimensions[col].width = 22

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=visitas_condominio.xlsx"},
    )


@app.get("/health")
def health():
    return {"ok": True}
