from io import BytesIO

import bcrypt
from fastapi import Cookie, FastAPI, File, Form, Query, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from core.auth import (
    condominio_actual_id,
    crear_token_sesion,
    no_permisos_response,
    puede_admin,
    puede_escribir_residentes,
    puede_escribir_vehiculos,
    puede_exportar,
    puede_superadmin,
    puede_ver_residentes,
    puede_ver_vehiculos,
    require_login,
    verificar_password_admin,
    verificar_password_superadmin,
)
from core.config import SUPERADMIN_USERNAME, superadmin_configurado
from core import database as database_core
from core.database import conectar, obtener_o_crear_departamento
from core.helpers import (
    badge_estado,
    encabezados_normalizados,
    format_depto,
    h,
    render_delete_action,
)
from core.layout import layout, render_resultado_importacion
from routers import dashboard, encomiendas, residentes, vehiculos, visitas

app = FastAPI()
app.include_router(visitas.router)
app.include_router(encomiendas.router)
app.include_router(dashboard.router)
app.include_router(residentes.router)
app.include_router(vehiculos.router)

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


def render_login_form(condominio_slug: str, condominio_nombre: str, msg: str = ""):
    msg_html = f"<p class='muted'>{h(msg)}</p>" if msg else ""
    contenido = f"""
    <div class="card" style="max-width:460px;margin:auto;">
        <h2>Acceso · {h(condominio_nombre)}</h2>
        <p class="muted">Condominio: <strong>{h(condominio_slug)}</strong></p>
        {msg_html}
        <form action="/c/{h(condominio_slug)}/login" method="post">
            <label>Usuario<input name="username" placeholder="Usuario" required></label>
            <label>Contraseña<input name="password" type="password" placeholder="Contraseña" required></label>
            <button class="full" type="submit">Entrar</button>
        </form>
        <div class="actions"><a class="btn dark" href="/">Volver</a></div>
    </div>
    """
    return layout("Login", contenido)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_form():
    return RedirectResponse(url="/c/demo/login", status_code=303)


@app.get("/c/{slug}/login", response_class=HTMLResponse)
def condominio_login_form(slug: str, msg: str = Query(default="")):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, activo FROM condominios WHERE slug = %s", (slug,))
            condo = cursor.fetchone()
    if not condo or not condo[2]:
        return HTMLResponse("<h3>Condominio no disponible.</h3>", status_code=404)
    return render_login_form(slug, condo[1], msg)


def login_en_condominio(slug: str, username: str, password: str):
    usuario_db = None
    condo = None
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, slug, activo FROM condominios WHERE slug = %s", (slug,))
            condo = cursor.fetchone()
            if not condo or not condo[3]:
                return HTMLResponse("<h3>Condominio no disponible.</h3>", status_code=404)
            cursor.execute(
                """
                SELECT username, password_hash, rol, activo
                FROM usuarios
                WHERE username = %s AND condominio_id = %s
                """,
                (username, condo[0]),
            )
            usuario_db = cursor.fetchone()

    login_ok = False
    rol = "admin"
    if usuario_db and usuario_db[3]:
        login_ok = bcrypt.checkpw(password.encode("utf-8"), usuario_db[1].encode("utf-8"))
        rol = usuario_db[2]

    if not login_ok:
        return HTMLResponse(f"<h3>Credenciales incorrectas</h3><a href='/c/{h(slug)}/login'>Volver</a>", status_code=401)

    response = RedirectResponse(url="/?msg=Sesión+iniciada+con+éxito", status_code=303)
    response.set_cookie(
        key="admin_session",
        value=crear_token_sesion(
            username=username,
            rol=rol,
            condominio_id=condo[0],
            condominio_nombre=condo[1],
            condominio_slug=condo[2],
        ),
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response


@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    return login_en_condominio("demo", username, password)


@app.post("/c/{slug}/login")
def condominio_login(slug: str, username: str = Form(...), password: str = Form(...)):
    return login_en_condominio(slug, username, password)


@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/c/{slug}/logout")
def condominio_logout(slug: str):
    response = RedirectResponse(url=f"/c/{slug}/login?msg=Sesión+cerrada+correctamente", status_code=303)
    response.delete_cookie("admin_session")
    return response


@app.get("/c/{slug}/mi-cuenta", response_class=HTMLResponse)
def mi_cuenta_condominio(
    slug: str,
    msg: str = Query(default=""),
    admin_session: str | None = Cookie(default=None),
):
    usuario = require_login(admin_session)
    if not usuario or usuario.get("rol") not in {"admin", "guardia", "comite"}:
        return RedirectResponse(url=f"/c/{slug}/login", status_code=303)
    if usuario.get("condominio_slug") != slug:
        return no_permisos_response(usuario)
    msg_html = f"<p class='muted'>{h(msg)}</p>" if msg else ""
    contenido = f"""
    <div class="hero"><h1>Mi cuenta</h1><p>Gestiona tu perfil y contraseña.</p></div>
    <div class="card">
        <h2>Información</h2>
        <p><strong>Usuario:</strong> {h(usuario.get("username"))}</p>
        <p><strong>Rol:</strong> {h(usuario.get("rol"))}</p>
        <p><strong>Condominio:</strong> {h(usuario.get("condominio_nombre"))}</p>
    </div>
    <div class="card">
        <h2>Cambiar contraseña</h2>
        {msg_html}
        <form action="/c/{h(slug)}/mi-cuenta/cambiar-password" method="post">
            <label>Contraseña actual<input type="password" name="password_actual" required></label>
            <label>Nueva contraseña<input type="password" name="password_nueva" required></label>
            <label>Confirmar nueva contraseña<input type="password" name="password_confirmacion" required></label>
            <button class="full" type="submit">Actualizar contraseña</button>
        </form>
    </div>
    <div class="actions"><a class="btn" href="/">Inicio</a></div>
    """
    return layout("Mi cuenta", contenido, usuario)


@app.post("/c/{slug}/mi-cuenta/cambiar-password")
def cambiar_password_mi_cuenta(
    slug: str,
    password_actual: str = Form(...),
    password_nueva: str = Form(...),
    password_confirmacion: str = Form(...),
    admin_session: str | None = Cookie(default=None),
):
    usuario = require_login(admin_session)
    if not usuario or usuario.get("rol") not in {"admin", "guardia", "comite"}:
        return RedirectResponse(url=f"/c/{slug}/login", status_code=303)
    if usuario.get("condominio_slug") != slug:
        return no_permisos_response(usuario)
    if password_nueva != password_confirmacion:
        return RedirectResponse(url=f"/c/{slug}/mi-cuenta?msg=Las+contraseñas+nuevas+no+coinciden", status_code=303)
    if len(password_nueva) < 8:
        return RedirectResponse(
            url=f"/c/{slug}/mi-cuenta?msg=La+nueva+contraseña+debe+tener+al+menos+8+caracteres",
            status_code=303,
        )

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT password_hash
                FROM usuarios
                WHERE username = %s AND condominio_id = %s
                """,
                (usuario.get("username"), usuario.get("condominio_id")),
            )
            user_db = cursor.fetchone()
            if not user_db or not bcrypt.checkpw(password_actual.encode("utf-8"), user_db[0].encode("utf-8")):
                return RedirectResponse(url=f"/c/{slug}/mi-cuenta?msg=Contraseña+actual+incorrecta", status_code=303)

            nuevo_hash = bcrypt.hashpw(password_nueva.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute(
                """
                UPDATE usuarios
                SET password_hash = %s
                WHERE username = %s AND condominio_id = %s
                """,
                (nuevo_hash, usuario.get("username"), usuario.get("condominio_id")),
            )
        conn.commit()
    return RedirectResponse(url=f"/c/{slug}/mi-cuenta?msg=Contraseña+actualizada+correctamente", status_code=303)


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
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
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


@app.get("/admin/usuarios", response_class=HTMLResponse)
def admin_usuarios(admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    with conectar() as conn:
        with conn.cursor() as cursor:
            condominio_id = condominio_actual_id(usuario)
            cursor.execute(
                """
                SELECT id, username, rol, activo, creado_en
                FROM usuarios
                WHERE condominio_id = %s
                ORDER BY id ASC
                """,
                (condominio_id,),
            )
            data = cursor.fetchall()

    filas = ""
    for u in data:
        activo_badge = badge_estado("Activo", "success") if u[3] else badge_estado("Inactivo", "warning")
        accion_activo = "Desactivar" if u[3] else "Activar"
        filas += f"""
        <tr>
            <td>{u[0]}</td>
            <td>{h(u[1])}</td>
            <td>
                <form action="/admin/usuarios/rol/{u[0]}" method="post" style="display:flex;gap:8px;align-items:center;">
                    <select name="rol" style="min-width:140px;">
                        <option value="admin" {"selected" if u[2] == "admin" else ""}>admin</option>
                        <option value="guardia" {"selected" if u[2] == "guardia" else ""}>guardia</option>
                        <option value="comite" {"selected" if u[2] == "comite" else ""}>comite</option>
                    </select>
                    <button type="submit">Cambiar rol</button>
                </form>
            </td>
            <td>{activo_badge}</td>
            <td>{h(u[4])}</td>
            <td>
                <a class="btn dark" href="/admin/usuarios/toggle/{u[0]}">{accion_activo}</a>
                <a class="btn red" href="/admin/usuarios/eliminar/{u[0]}"
                   onclick="return confirm('¿Eliminar usuario {h(u[1])}?')">Eliminar</a>
            </td>
        </tr>
        """

    contenido = f"""
    <div class="hero"><h1>Usuarios</h1><p>Gestión de cuentas y roles del sistema.</p></div>
    <div class="card">
        <h2>Crear usuario</h2>
        <form action="/admin/usuarios/crear" method="post">
            <label>Username<input name="username" required placeholder="usuario"></label>
            <label>Password<input type="password" name="password" required placeholder="••••••••"></label>
            <label>Rol
                <select name="rol">
                    <option value="guardia">guardia</option>
                    <option value="comite">comite</option>
                    <option value="admin">admin</option>
                </select>
            </label>
            <button class="full" type="submit">Crear usuario</button>
        </form>
    </div>
    <div class="card">
        <h2>Listado de usuarios</h2>
        <div class="table-wrap"><table>
            <tr><th>ID</th><th>Username</th><th>Rol</th><th>Estado</th><th>Creado en</th><th>Acciones</th></tr>
            {filas}
        </table></div>
    </div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/dashboard-condominio">Dashboard</a>
    </div>
    """
    return layout("Admin usuarios", contenido, usuario)


@app.post("/admin/usuarios/crear")
def admin_usuarios_crear(
    admin_session: str | None = Cookie(default=None),
    username: str = Form(...),
    password: str = Form(...),
    rol: str = Form(...),
):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)
    if rol not in {"admin", "guardia", "comite"}:
        return HTMLResponse("Rol inválido", status_code=400)

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with conectar() as conn:
        with conn.cursor() as cursor:
            condominio_id = condominio_actual_id(usuario)
            cursor.execute(
                """
                INSERT INTO usuarios (username, password_hash, rol, activo, condominio_id)
                VALUES (%s, %s, %s, TRUE, %s)
                ON CONFLICT (condominio_id, username) DO NOTHING
                """,
                (username.strip(), password_hash, rol, condominio_id),
            )
        conn.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=303)


@app.get("/admin/usuarios/toggle/{user_id}")
def admin_usuarios_toggle(user_id: int, admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username, activo FROM usuarios WHERE id = %s AND condominio_id = %s",
                (user_id, condominio_actual_id(usuario)),
            )
            user = cursor.fetchone()
            if not user:
                return RedirectResponse(url="/admin/usuarios", status_code=303)
            if user[0] == usuario.get("username"):
                return HTMLResponse("No puedes desactivar tu propio usuario.", status_code=400)
            cursor.execute(
                "UPDATE usuarios SET activo = NOT activo WHERE id = %s AND condominio_id = %s",
                (user_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=303)


@app.post("/admin/usuarios/rol/{user_id}")
def admin_usuarios_cambiar_rol(
    user_id: int,
    admin_session: str | None = Cookie(default=None),
    rol: str = Form(...),
):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)
    if rol not in {"admin", "guardia", "comite"}:
        return HTMLResponse("Rol inválido", status_code=400)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET rol = %s WHERE id = %s AND condominio_id = %s",
                (rol, user_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=303)


@app.get("/admin/usuarios/eliminar/{user_id}")
def admin_usuarios_eliminar(user_id: int, admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT username FROM usuarios WHERE id = %s AND condominio_id = %s",
                (user_id, condominio_actual_id(usuario)),
            )
            user = cursor.fetchone()
            if user and user[0] == usuario.get("username"):
                return HTMLResponse("No puedes eliminar tu propio usuario.", status_code=400)
            cursor.execute(
                "DELETE FROM usuarios WHERE id = %s AND condominio_id = %s",
                (user_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=303)


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


@app.get("/exportar/visitas")
def exportar_visitas(admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_exportar(usuario):
        return no_permisos_response(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT v.id, v.nombre, v.rut, v.patente, d.torre, d.numero, v.autorizado_por,
                       v.observacion, v.hora_ingreso, v.hora_salida
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                WHERE v.condominio_id = %s
                ORDER BY v.id DESC
                """,
                (condominio_actual_id(usuario),),
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

    for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        ws.column_dimensions[col].width = 22

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=visitas_condominio.xlsx"},
    )


@app.get("/exportar/encomiendas")
def exportar_encomiendas(admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_exportar(usuario):
        return no_permisos_response(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.id, e.nombre_receptor, d.torre, d.numero, e.descripcion, e.recibido_por,
                       e.fecha_recepcion, e.entregado, e.fecha_entrega, e.entregado_a, e.observacion
                FROM encomiendas e
                LEFT JOIN departamentos d ON e.departamento_id = d.id
                WHERE e.condominio_id = %s
                ORDER BY e.id DESC
                """,
                (condominio_actual_id(usuario),),
            )
            data = cursor.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Encomiendas"

    headers = [
        "ID",
        "Nombre receptor",
        "Torre",
        "Departamento",
        "Descripción",
        "Recibido por",
        "Fecha recepción",
        "Entregado",
        "Fecha entrega",
        "Entregado a",
        "Observación",
    ]
    ws.append(headers)

    fill = PatternFill(fill_type="solid", fgColor="2563EB")
    font = Font(color="FFFFFF", bold=True)
    align = Alignment(horizontal="center")
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align

    for row in data:
        ws.append(list(row))

    for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
        ws.column_dimensions[col].width = 22

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)

    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=encomiendas_condominio.xlsx"},
    )


@app.get("/health")
def health():
    return {"ok": True}




