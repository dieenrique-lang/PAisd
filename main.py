from fastapi import Cookie, FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import (
    condominio_actual_id,
    crear_token_sesion,
    hash_password,
    no_permisos_response,
    puede_admin,
    puede_superadmin,
    require_login,
    verificar_password_superadmin,
)
from core.config import SUPERADMIN_USERNAME, superadmin_configurado
from core import database as database_core
from core.database import conectar
from core.helpers import (
    badge_estado,
    h,
)
from core.layout import layout
from routers import dashboard, encomiendas, exportar, importar, login, residentes, usuarios, vehiculos, visitas

app = FastAPI()
app.include_router(visitas.router)
app.include_router(encomiendas.router)
app.include_router(dashboard.router)
app.include_router(residentes.router)
app.include_router(vehiculos.router)
app.include_router(importar.router)
app.include_router(exportar.router)
app.include_router(usuarios.router)
app.include_router(login.router)

@app.on_event("startup")
def startup_event():
    try:
        database_core.crear_tablas()
    except Exception as exc:
        print(f"[startup] No se pudieron crear/verificar tablas: {exc}")


@app.get("/", response_class=HTMLResponse)
def inicio(msg: str = Query(default=""), admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    superadmin_btn = '<a class="btn dark" href="/superadmin/login">Acceso superadmin</a>' if superadmin_configurado() else ""
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT nombre, slug
                FROM condominios
                WHERE activo = TRUE
                ORDER BY nombre ASC
                """
            )
            condominios_activos = cursor.fetchall()

    if condominios_activos:
        filas_condominios = "".join(
            f"""
            <tr>
                <td>{h(c[0])}</td>
                <td><a class="btn" href="/c/{h(c[1])}/login">Ingresar</a></td>
            </tr>
            """
            for c in condominios_activos
        )
        selector_condominio = f"""
        <div class="card">
            <h2>Selecciona tu condominio</h2>
            <div class="table-wrap"><table>
                <tr><th>Condominio</th><th>Acceso</th></tr>
                {filas_condominios}
            </table></div>
        </div>
        """
    else:
        selector_condominio = """
        <div class="card">
            <h2>Selecciona tu condominio</h2>
            <p class="muted">No hay condominios disponibles por el momento.</p>
        </div>
        """

    msg_html = f"<div class='card'><p>{h(msg)}</p></div>" if msg else ""
    menu_modulos = f"""
    <div class="hero">
        <h1>Panel principal</h1>
        <p>Operación diaria del condominio en un solo lugar.</p>
    </div>
    {msg_html}
    {selector_condominio}
    <div class="card">
        <h2>Menú principal</h2>
        <div class="actions">
            <a class="btn" href="/residentes">Residentes</a>
            <a class="btn" href="/vehiculos">Vehículos</a>
            <a class="btn" href="/visitas">Control de visitas</a>
            <a class="btn" href="/encomiendas">Encomiendas</a>
            <a class="btn" href="/dashboard-condominio">Dashboard</a>
            {superadmin_btn}
        </div>
    </div>
    """
    contenido_publico = f"""
    <div class="hero">
        <h1>Panel principal</h1>
        <p>Selecciona tu condominio para iniciar sesión.</p>
    </div>
    {msg_html}
    {selector_condominio}
    <div class="actions">
        {superadmin_btn}
    </div>
    """
    contenido = menu_modulos if usuario else contenido_publico
    return layout("CondoControl", contenido, usuario)


@app.get("/superadmin/login", response_class=HTMLResponse)
def superadmin_login_form():
    if not superadmin_configurado():
        return HTMLResponse(
            layout(
                "Superadmin no configurado",
                """
                <div class="card" style="max-width:560px;margin:auto;">
                    <h2>Acceso superadmin no configurado</h2>
                    <p class="muted">Define SUPERADMIN_USERNAME y SUPERADMIN_PASSWORD_HASH para habilitar este acceso.</p>
                    <div class="actions"><a class="btn dark" href="/">Volver</a></div>
                </div>
                """,
            ),
            status_code=503,
        )
    contenido = """
    <div class="card" style="max-width:460px;margin:auto;">
        <h2>Acceso Superadmin</h2>
        <form action="/superadmin/login" method="post">
            <label>Usuario<input name="username" placeholder="Usuario" required></label>
            <label>Contraseña<input name="password" type="password" placeholder="Contraseña" required></label>
            <button class="full" type="submit">Entrar</button>
        </form>
        <div class="actions"><a class="btn dark" href="/">Volver</a></div>
    </div>
    """
    return layout("Login superadmin", contenido)


@app.post("/superadmin/login")
def superadmin_login(username: str = Form(...), password: str = Form(...)):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    if username != SUPERADMIN_USERNAME or not verificar_password_superadmin(password):
        return HTMLResponse("<h3>Credenciales superadmin inválidas.</h3><a href='/superadmin/login'>Volver</a>", status_code=401)
    response = RedirectResponse(url="/superadmin", status_code=303)
    response.set_cookie(
        key="admin_session",
        value=crear_token_sesion(username=SUPERADMIN_USERNAME, rol="superadmin"),
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@app.get("/superadmin/logout")
def superadmin_logout():
    response = RedirectResponse(url="/superadmin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/superadmin", response_class=HTMLResponse)
def superadmin_panel(msg: str = Query(default=""), admin_session: str | None = Cookie(default=None)):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, slug, activo, creado_en FROM condominios ORDER BY id ASC")
            data = cursor.fetchall()
    filas = "".join(
        f"""
        <tr>
            <td>{h(c[1])}</td>
            <td>{h(c[2])}</td>
            <td>{badge_estado('Activo','success') if c[3] else badge_estado('Inactivo','warning')}</td>
            <td><a class='btn' href='/c/{h(c[2])}/login'>Ingresar</a></td>
            <td><a class='btn dark' href='/superadmin/condominios/{c[0]}/crear-admin'>Crear admin</a></td>
            <td><a class='btn dark' href='/superadmin/condominios/toggle/{c[0]}'>Activar/Desactivar</a></td>
            <td>
                <form action="/superadmin/condominios/{c[0]}/eliminar" method="post" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;" onsubmit="return confirm('Esta acción eliminará todo el condominio. ¿Continuar?');">
                    <input name="confirmacion" placeholder="ELIMINAR" required style="min-width:110px;">
                    <button class="btn red" type="submit">Eliminar</button>
                </form>
            </td>
        </tr>
        """
        for c in data
    )
    msg_html = f"<div class='card'><p>{h(msg)}</p></div>" if msg else ""
    contenido = f"""
    <div class="hero"><h1>Panel multi-condominio</h1><p>Administración global de condominios.</p></div>
    {msg_html}
    <div class="actions">
        <a class="btn" href="/superadmin/condominios/nuevo">Crear condominio</a>
        <a class="btn dark" href="/superadmin/logout">Cerrar sesión superadmin</a>
    </div>
    <div class="card"><h2>Condominios</h2><div class="table-wrap"><table>
    <tr><th>Nombre</th><th>Slug</th><th>Estado</th><th>Acceso</th><th>Admin inicial</th><th>Estado</th><th>Eliminar</th></tr>
    {filas}
    </table></div></div>
    """
    return layout("Panel multi-condominio", contenido, usuario)


@app.get("/superadmin/condominios/nuevo", response_class=HTMLResponse)
def superadmin_condominio_nuevo_form(admin_session: str | None = Cookie(default=None)):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    contenido = """
    <div class="hero"><h1>Crear condominio</h1><p>Alta de nuevo condominio.</p></div>
    <div class="card">
        <form action="/superadmin/condominios/nuevo" method="post">
            <label>Nombre<input name="nombre" required></label>
            <label>Slug<input name="slug" required placeholder="condominio-los-aromos"></label>
            <button class="full" type="submit">Crear condominio</button>
        </form>
    </div>
    """
    return layout("Nuevo condominio", contenido, usuario)


@app.post("/superadmin/condominios/nuevo")
def superadmin_condominio_nuevo(
    admin_session: str | None = Cookie(default=None),
    nombre: str = Form(...),
    slug: str = Form(...),
):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    slug_limpio = slug.strip().lower()
    if " " in slug_limpio or not slug_limpio:
        return HTMLResponse("Slug inválido. Usa minúsculas y sin espacios.", status_code=400)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO condominios (nombre, slug, activo) VALUES (%s, %s, TRUE) ON CONFLICT (slug) DO NOTHING",
                (nombre.strip(), slug_limpio),
            )
        conn.commit()
    return RedirectResponse(url="/superadmin", status_code=303)


@app.get("/superadmin/condominios/{condominio_id}/crear-admin", response_class=HTMLResponse)
def superadmin_crear_admin_form(condominio_id: int, admin_session: str | None = Cookie(default=None)):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT nombre, slug FROM condominios WHERE id = %s", (condominio_id,))
            condo = cursor.fetchone()
    if not condo:
        return HTMLResponse("Condominio no encontrado", status_code=404)
    contenido = f"""
    <div class="hero"><h1>Crear admin inicial</h1><p>{h(condo[0])} · {h(condo[1])}</p></div>
    <div class="card">
        <form action="/superadmin/condominios/{condominio_id}/crear-admin" method="post">
            <label>Username<input name="username" required></label>
            <label>Password<input type="password" name="password" required></label>
            <button class="full" type="submit">Crear admin</button>
        </form>
    </div>
    """
    return layout("Crear admin condominio", contenido, usuario)


@app.post("/superadmin/condominios/{condominio_id}/crear-admin")
def superadmin_crear_admin(
    condominio_id: int,
    admin_session: str | None = Cookie(default=None),
    username: str = Form(...),
    password: str = Form(...),
):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    password_hash = hash_password(password)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM condominios WHERE id = %s", (condominio_id,))
            if not cursor.fetchone():
                return HTMLResponse("Condominio no encontrado", status_code=404)
            cursor.execute(
                """
                INSERT INTO usuarios (username, password_hash, rol, activo, condominio_id)
                VALUES (%s, %s, 'admin', TRUE, %s)
                ON CONFLICT (condominio_id, username) DO NOTHING
                """,
                (username.strip(), password_hash, condominio_id),
            )
        conn.commit()
    return RedirectResponse(url="/superadmin", status_code=303)


@app.get("/superadmin/condominios/toggle/{condominio_id}")
def superadmin_condominios_toggle(condominio_id: int, admin_session: str | None = Cookie(default=None)):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE condominios SET activo = NOT activo WHERE id = %s", (condominio_id,))
        conn.commit()
    return RedirectResponse(url="/superadmin", status_code=303)


@app.post("/superadmin/condominios/{condominio_id}/eliminar")
def superadmin_condominio_eliminar(
    condominio_id: int,
    confirmacion: str = Form(...),
    admin_session: str | None = Cookie(default=None),
):
    if not superadmin_configurado():
        return HTMLResponse("Acceso superadmin no configurado", status_code=503)
    usuario = require_login(admin_session)
    if not puede_superadmin(usuario):
        return RedirectResponse(url="/superadmin/login", status_code=303)
    if confirmacion.strip() != "ELIMINAR":
        return RedirectResponse(url="/superadmin?msg=Debes+escribir+exactamente+ELIMINAR", status_code=303)

    conn = None
    try:
        conn = conectar()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM condominios WHERE activo = TRUE")
            activos = cursor.fetchone()[0]
            cursor.execute("SELECT activo FROM condominios WHERE id = %s", (condominio_id,))
            target = cursor.fetchone()
            if not target:
                return RedirectResponse(url="/superadmin?msg=Condominio+no+encontrado", status_code=303)
            if target[0] and activos <= 1:
                return RedirectResponse(url="/superadmin?msg=No+se+puede+eliminar+el+último+condominio+activo.", status_code=303)

            cursor.execute("DELETE FROM visitas WHERE condominio_id = %s;", (condominio_id,))
            cursor.execute("DELETE FROM encomiendas WHERE condominio_id = %s;", (condominio_id,))
            cursor.execute("DELETE FROM vehiculos WHERE condominio_id = %s;", (condominio_id,))
            cursor.execute("DELETE FROM residentes WHERE condominio_id = %s;", (condominio_id,))
            cursor.execute("DELETE FROM departamentos WHERE condominio_id = %s;", (condominio_id,))
            cursor.execute("DELETE FROM usuarios WHERE condominio_id = %s;", (condominio_id,))
            cursor.execute("DELETE FROM condominios WHERE id = %s;", (condominio_id,))
        conn.commit()
        return RedirectResponse(url="/superadmin?msg=Condominio+eliminado+correctamente", status_code=303)
    except Exception:
        if conn:
            conn.rollback()
        return RedirectResponse(url="/superadmin?msg=Error+al+eliminar+condominio", status_code=303)
    finally:
        if conn:
            conn.close()


@app.get("/admin/restablecer", response_class=HTMLResponse)
def admin_restablecer_form(admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    contenido = """
    <div class="hero"><h1>Restablecer datos de fábrica</h1><p>Herramienta de preparación antes de producción.</p></div>
    <div class="card" style="border:2px solid #dc2626;">
        <h2 style="color:#b91c1c;">Zona peligrosa</h2>
        <p class="muted">
            Esta acción eliminará permanentemente todos los residentes, vehículos, visitas, encomiendas y departamentos,
            incluyendo datos importados desde Excel. No se eliminarán usuarios.
        </p>
        <form action="/admin/restablecer" method="post">
            <label>Escribe exactamente RESTABLECER para confirmar
                <input name="confirmacion" placeholder="RESTABLECER" required>
            </label>
            <button class="full btn red" type="submit">Restablecer datos</button>
        </form>
    </div>
    <div class="actions"><a class="btn" href="/">Volver</a></div>
    """
    return layout("Restablecer datos", contenido, usuario)


@app.post("/admin/restablecer")
def admin_restablecer(
    admin_session: str | None = Cookie(default=None),
    confirmacion: str = Form(...),
):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    if confirmacion.strip() != "RESTABLECER":
        return HTMLResponse(
            layout(
                "Restablecer datos",
                """
                <div class="card" style="border:2px solid #dc2626;">
                    <h2 style="color:#b91c1c;">Confirmación inválida</h2>
                    <p>Debes escribir exactamente <strong>RESTABLECER</strong>.</p>
                    <div class="actions"><a class="btn" href="/admin/restablecer">Volver</a></div>
                </div>
                """,
                usuario,
            ),
            status_code=400,
        )

    tablas_operativas = ("residentes", "vehiculos", "visitas", "encomiendas", "departamentos")
    resumen = {tabla: -1 for tabla in tablas_operativas}
    condominio_id = condominio_actual_id(usuario)
    conn = None
    try:
        conn = conectar()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM visitas WHERE condominio_id = %s", (condominio_id,))
            cursor.execute("DELETE FROM encomiendas WHERE condominio_id = %s", (condominio_id,))
            cursor.execute("DELETE FROM vehiculos WHERE condominio_id = %s", (condominio_id,))
            cursor.execute("DELETE FROM residentes WHERE condominio_id = %s", (condominio_id,))
            cursor.execute("DELETE FROM departamentos WHERE condominio_id = %s", (condominio_id,))

            for tabla in tablas_operativas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE condominio_id = %s", (condominio_id,))
                resumen[tabla] = cursor.fetchone()[0]

            if any(conteo > 0 for conteo in resumen.values()):
                raise RuntimeError("No fue posible restablecer completamente todas las tablas operativas.")
        conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        return HTMLResponse(
            layout(
                "Restablecer datos",
                f"""
                <div class="card" style="border:2px solid #dc2626;">
                    <h2 style="color:#b91c1c;">Error al restablecer datos</h2>
                    <p>{h(exc)}</p>
                    <div class="actions"><a class="btn" href="/admin/restablecer">Volver</a></div>
                </div>
                """,
                usuario,
            ),
            status_code=500,
        )
    finally:
        if conn:
            conn.close()

    contenido = f"""
    <div class="hero"><h1>Restablecimiento completado</h1><p>Se eliminaron los datos operativos del condominio.</p></div>
    <div class="card">
        <h2>Resumen</h2>
        <ul>
            <li>residentes: <strong>{resumen['residentes']}</strong></li>
            <li>vehiculos: <strong>{resumen['vehiculos']}</strong></li>
            <li>visitas: <strong>{resumen['visitas']}</strong></li>
            <li>encomiendas: <strong>{resumen['encomiendas']}</strong></li>
            <li>departamentos: <strong>{resumen['departamentos']}</strong></li>
        </ul>
        <p class="muted">Usuarios, credenciales y roles no fueron eliminados.</p>
        <div class="actions"><a class="btn" href="/">Volver al inicio</a></div>
    </div>
    """
    return HTMLResponse(layout("Restablecimiento completado", contenido, usuario))


@app.get("/health")
def health():
    return {"ok": True}








