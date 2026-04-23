from fastapi import FastAPI, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from datetime import datetime
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from itsdangerous import URLSafeSerializer, BadSignature
import bcrypt
import os
import psycopg

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esto")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

serializer = URLSafeSerializer(SECRET_KEY, salt="admin-session")


def conectar():
    return psycopg.connect(DATABASE_URL)


def crear_tablas():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS departamentos (
                    id SERIAL PRIMARY KEY,
                    torre TEXT,
                    numero TEXT NOT NULL,
                    UNIQUE(torre, numero)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS residentes (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    telefono TEXT,
                    email TEXT,
                    tipo TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehiculos (
                    id SERIAL PRIMARY KEY,
                    patente TEXT NOT NULL,
                    marca TEXT,
                    modelo TEXT,
                    color TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visitas (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    rut TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id),
                    autorizado_por TEXT,
                    observacion TEXT,
                    hora_ingreso TIMESTAMP DEFAULT NOW(),
                    hora_salida TIMESTAMP
                )
            """)
        conn.commit()


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
    return bcrypt.checkpw(
        password.encode("utf-8"),
        ADMIN_PASSWORD_HASH.encode("utf-8")
    )


crear_tablas()


def layout(titulo, contenido):
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{titulo}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                margin: 0;
                padding: 30px;
                color: #1f2937;
            }}
            .wrap {{
                max-width: 1100px;
                margin: auto;
            }}
            .hero {{
                background: linear-gradient(135deg, #1d4ed8, #0f172a);
                color: white;
                padding: 25px;
                border-radius: 18px;
                margin-bottom: 20px;
            }}
            .card {{
                background: white;
                padding: 22px;
                border-radius: 16px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
                margin-bottom: 18px;
            }}
            input, select, textarea {{
                width: 100%;
                padding: 11px;
                margin: 7px 0;
                border-radius: 9px;
                border: 1px solid #d1d5db;
                box-sizing: border-box;
            }}
            button, .btn {{
                display: inline-block;
                background: #2563eb;
                color: white;
                padding: 10px 15px;
                border-radius: 10px;
                border: none;
                text-decoration: none;
                font-weight: bold;
                cursor: pointer;
                margin: 5px;
            }}
            .btn.dark {{
                background: #0f172a;
            }}
            .btn.red {{
                background: #dc2626;
            }}
            .btn.green {{
                background: #16a34a;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 14px;
                overflow: hidden;
            }}
            th {{
                background: #2563eb;
                color: white;
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 10px;
                border-bottom: 1px solid #e5e7eb;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
            }}
            .stat {{
                font-size: 32px;
                font-weight: bold;
                color: #2563eb;
            }}
            a {{
                color: #2563eb;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="wrap">
            {contenido}
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def inicio():
    contenido = """
    <div class="hero">
        <h1>CondoControl</h1>
        <p>Sistema simple de control de residentes, vehículos y visitas para condominios.</p>
    </div>

    <div class="card">
        <h2>Menú principal</h2>
        <a class="btn" href="/residentes">Residentes</a>
        <a class="btn" href="/vehiculos">Vehículos</a>
        <a class="btn" href="/visitas">Control de visitas</a>
        <a class="btn" href="/dashboard-condominio">Dashboard</a>
        <a class="btn dark" href="/admin/login">Acceso administrador</a>
    </div>
    """
    return layout("CondoControl", contenido)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form():
    contenido = """
    <div class="card" style="max-width:400px;margin:auto;">
        <h2>Acceso administrador</h2>
        <form action="/admin/login" method="post">
            <input name="username" placeholder="Usuario" required>
            <input name="password" type="password" placeholder="Contraseña" required>
            <button type="submit">Entrar</button>
        </form>
        <a href="/">Volver</a>
    </div>
    """
    return layout("Login admin", contenido)


@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if username != ADMIN_USERNAME or not verificar_password_admin(password):
        return HTMLResponse("<h3>Credenciales incorrectas</h3><a href='/admin/login'>Volver</a>", status_code=401)

    response = RedirectResponse(url="/residentes", status_code=303)
    response.set_cookie(
        key="admin_session",
        value=crear_token_admin(),
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response


@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/residentes", response_class=HTMLResponse)
def residentes(admin_session: str | None = Cookie(default=None)):
    es_admin = require_admin(admin_session)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.id, r.nombre, r.telefono, r.email, r.tipo, d.torre, d.numero
                FROM residentes r
                LEFT JOIN departamentos d ON r.departamento_id = d.id
                ORDER BY r.id DESC
            """)
            residentes = cursor.fetchall()

    filas = ""
    for r in residentes:
        acciones = ""
        if es_admin:
            acciones = f"""
            <a class="btn red" href="/eliminar-residente/{r[0]}"
            onclick="return confirm('¿Eliminar residente?')">Eliminar</a>
            """
        else:
            acciones = "Solo admin"

        filas += f"""
        <tr>
            <td>{r[1]}</td>
            <td>{r[5] or ''}-{r[6] or ''}</td>
            <td>{r[2] or ''}</td>
            <td>{r[3] or ''}</td>
            <td>{r[4] or ''}</td>
            <td>{acciones}</td>
        </tr>
        """

    logout = '<a class="btn dark" href="/admin/logout">Cerrar sesión admin</a>' if es_admin else ""

    contenido = f"""
    <div class="hero">
        <h1>Residentes</h1>
        <p>Registro de residentes por departamento.</p>
    </div>

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
            <button type="submit">Guardar residente</button>
        </form>
    </div>

    <div class="card">
        <h2>Listado</h2>
        <table>
            <tr>
                <th>Nombre</th>
                <th>Depto</th>
                <th>Teléfono</th>
                <th>Email</th>
                <th>Tipo</th>
                <th>Acción</th>
            </tr>
            {filas}
        </table>
    </div>

    <a class="btn" href="/">Inicio</a>
    <a class="btn" href="/dashboard-condominio">Dashboard</a>
    {logout}
    """
    return layout("Residentes", contenido)


def obtener_o_crear_departamento(cursor, torre, numero):
    cursor.execute("""
        SELECT id FROM departamentos
        WHERE COALESCE(torre, '') = COALESCE(%s, '') AND numero = %s
    """, (torre, numero))
    dep = cursor.fetchone()

    if dep:
        return dep[0]

    cursor.execute("""
        INSERT INTO departamentos (torre, numero)
        VALUES (%s, %s)
        RETURNING id
    """, (torre, numero))
    return cursor.fetchone()[0]


@app.post("/guardar-residente")
def guardar_residente(
    nombre: str = Form(...),
    telefono: str = Form(""),
    email: str = Form(""),
    tipo: str = Form("Residente"),
    torre: str = Form(""),
    numero: str = Form(...)
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, torre, numero)
            cursor.execute("""
                INSERT INTO residentes (nombre, telefono, email, tipo, departamento_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, telefono, email, tipo, dep_id))
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
            cursor.execute("""
                SELECT v.id, v.patente, v.marca, v.modelo, v.color, d.torre, d.numero
                FROM vehiculos v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                ORDER BY v.id DESC
            """)
            vehiculos = cursor.fetchall()

    filas = ""
    for v in vehiculos:
        acciones = ""
        if es_admin:
            acciones = f"""
            <a class="btn red" href="/eliminar-vehiculo/{v[0]}"
            onclick="return confirm('¿Eliminar vehículo?')">Eliminar</a>
            """
        else:
            acciones = "Solo admin"

        filas += f"""
        <tr>
            <td>{v[1]}</td>
            <td>{v[2] or ''}</td>
            <td>{v[3] or ''}</td>
            <td>{v[4] or ''}</td>
            <td>{v[5] or ''}-{v[6] or ''}</td>
            <td>{acciones}</td>
        </tr>
        """

    contenido = f"""
    <div class="hero">
        <h1>Vehículos</h1>
        <p>Registro de autos por departamento.</p>
    </div>

    <div class="card">
        <h2>Agregar vehículo</h2>
        <form action="/guardar-vehiculo" method="post">
            <input name="patente" placeholder="Patente" required>
            <input name="marca" placeholder="Marca">
            <input name="modelo" placeholder="Modelo">
            <input name="color" placeholder="Color">
            <input name="torre" placeholder="Torre / Block">
            <input name="numero" placeholder="Departamento" required>
            <button type="submit">Guardar vehículo</button>
        </form>
    </div>

    <div class="card">
        <h2>Listado vehículos</h2>
        <table>
            <tr>
                <th>Patente</th>
                <th>Marca</th>
                <th>Modelo</th>
                <th>Color</th>
                <th>Depto</th>
                <th>Acción</th>
            </tr>
            {filas}
        </table>
    </div>

    <a class="btn" href="/">Inicio</a>
    """
    return layout("Vehículos", contenido)


@app.post("/guardar-vehiculo")
def guardar_vehiculo(
    patente: str = Form(...),
    marca: str = Form(""),
    modelo: str = Form(""),
    color: str = Form(""),
    torre: str = Form(""),
    numero: str = Form(...)
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, torre, numero)
            cursor.execute("""
                INSERT INTO vehiculos (patente, marca, modelo, color, departamento_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (patente.upper(), marca, modelo, color, dep_id))
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
def visitas():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT v.id, v.nombre, v.rut, d.torre, d.numero, v.autorizado_por,
                       v.observacion, v.hora_ingreso, v.hora_salida
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                ORDER BY v.id DESC
                LIMIT 100
            """)
            visitas = cursor.fetchall()

    filas = ""
    for v in visitas:
        estado = "Dentro" if v[8] is None else "Salió"
        salida = f"<a class='btn green' href='/salida-visita/{v[0]}'>Marcar salida</a>" if v[8] is None else v[8]

        filas += f"""
        <tr>
            <td>{v[1]}</td>
            <td>{v[2] or ''}</td>
            <td>{v[3] or ''}-{v[4] or ''}</td>
            <td>{v[5] or ''}</td>
            <td>{v[7]}</td>
            <td>{estado}</td>
            <td>{salida}</td>
        </tr>
        """

    contenido = f"""
    <div class="hero">
        <h1>Control de visitas</h1>
        <p>Vista simple para guardia: registrar ingreso y marcar salida.</p>
    </div>

    <div class="card">
        <h2>Registrar ingreso</h2>
        <form action="/guardar-visita" method="post">
            <input name="nombre" placeholder="Nombre visita" required>
            <input name="rut" placeholder="RUT / Documento">
            <input name="torre" placeholder="Torre / Block">
            <input name="numero" placeholder="Departamento que visita" required>
            <input name="autorizado_por" placeholder="Autorizado por">
            <textarea name="observacion" placeholder="Observación"></textarea>
            <button type="submit">Registrar ingreso</button>
        </form>
    </div>

    <div class="card">
        <h2>Últimas visitas</h2>
        <table>
            <tr>
                <th>Visita</th>
                <th>RUT</th>
                <th>Depto</th>
                <th>Autoriza</th>
                <th>Ingreso</th>
                <th>Estado</th>
                <th>Salida</th>
            </tr>
            {filas}
        </table>
    </div>

    <a class="btn" href="/">Inicio</a>
    <a class="btn" href="/exportar/visitas">Exportar visitas</a>
    """
    return layout("Visitas", contenido)


@app.post("/guardar-visita")
def guardar_visita(
    nombre: str = Form(...),
    rut: str = Form(""),
    torre: str = Form(""),
    numero: str = Form(...),
    autorizado_por: str = Form(""),
    observacion: str = Form("")
):
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, torre, numero)
            cursor.execute("""
                INSERT INTO visitas (nombre, rut, departamento_id, autorizado_por, observacion)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, rut, dep_id, autorizado_por, observacion))
        conn.commit()

    return RedirectResponse(url="/visitas", status_code=303)


@app.get("/salida-visita/{visita_id}")
def salida_visita(visita_id: int):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE visitas
                SET hora_salida = NOW()
                WHERE id = %s AND hora_salida IS NULL
            """, (visita_id,))
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

            cursor.execute("""
                SELECT d.torre, d.numero, COUNT(v.id) AS total
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                GROUP BY d.torre, d.numero
                ORDER BY total DESC
                LIMIT 5
            """)
            top_deptos = cursor.fetchall()

    top_html = ""
    for d in top_deptos:
        top_html += f"<li>{d[0] or ''}-{d[1] or ''}: {d[2]} visitas</li>"

    contenido = f"""
    <div class="hero">
        <h1>Dashboard Condominio</h1>
        <p>Resumen operativo para administración y comité.</p>
    </div>

    <div class="grid">
        <div class="card">
            <h3>Residentes</h3>
            <div class="stat">{total_residentes}</div>
        </div>
        <div class="card">
            <h3>Vehículos</h3>
            <div class="stat">{total_vehiculos}</div>
        </div>
        <div class="card">
            <h3>Visitas hoy</h3>
            <div class="stat">{visitas_hoy}</div>
        </div>
        <div class="card">
            <h3>Visitas dentro</h3>
            <div class="stat">{visitas_dentro}</div>
        </div>
    </div>

    <div class="card">
        <h2>Top departamentos con más visitas</h2>
        <ul>{top_html or '<li>No hay datos</li>'}</ul>
    </div>

    <a class="btn" href="/">Inicio</a>
    <a class="btn" href="/visitas">Control visitas</a>
    <a class="btn" href="/exportar/visitas">Exportar visitas</a>
    """
    return layout("Dashboard Condominio", contenido)


@app.get("/exportar/visitas")
def exportar_visitas():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT v.id, v.nombre, v.rut, d.torre, d.numero, v.autorizado_por,
                       v.observacion, v.hora_ingreso, v.hora_salida
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                ORDER BY v.id DESC
            """)
            visitas = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Visitas"

    headers = [
        "ID", "Nombre visita", "RUT", "Torre", "Departamento",
        "Autorizado por", "Observación", "Hora ingreso", "Hora salida"
    ]
    ws.append(headers)

    fill = PatternFill(fill_type="solid", fgColor="2563EB")
    font = Font(color="FFFFFF", bold=True)
    align = Alignment(horizontal="center")

    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align

    for v in visitas:
        ws.append(list(v))

    for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]:
        ws.column_dimensions[col].width = 22

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=visitas_condominio.xlsx"}
    )


@app.get("/health")
def health():
    return {"ok": True}
