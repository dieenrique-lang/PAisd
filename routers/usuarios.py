from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import (
    condominio_actual_id,
    hash_password,
    no_permisos_response,
    puede_admin,
    require_login,
    verificar_password,
)
from core.database import get_conn
from core.helpers import badge_estado, h
from core.layout import layout


router = APIRouter()


@router.get("/c/{slug}/mi-cuenta", response_class=HTMLResponse)
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


@router.post("/c/{slug}/mi-cuenta/cambiar-password")
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

    with get_conn() as conn:
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
            if not user_db or not verificar_password(password_actual, user_db[0]):
                return RedirectResponse(url=f"/c/{slug}/mi-cuenta?msg=Contraseña+actual+incorrecta", status_code=303)

            nuevo_hash = hash_password(password_nueva)
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


@router.get("/admin/usuarios", response_class=HTMLResponse)
def admin_usuarios(admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    with get_conn() as conn:
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


@router.post("/admin/usuarios/crear")
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

    password_hash = hash_password(password)
    with get_conn() as conn:
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


@router.get("/admin/usuarios/toggle/{user_id}")
def admin_usuarios_toggle(user_id: int, admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    with get_conn() as conn:
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


@router.post("/admin/usuarios/rol/{user_id}")
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

    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE usuarios SET rol = %s WHERE id = %s AND condominio_id = %s",
                (rol, user_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/admin/usuarios", status_code=303)


@router.get("/admin/usuarios/eliminar/{user_id}")
def admin_usuarios_eliminar(user_id: int, admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_admin(usuario):
        return no_permisos_response(usuario)

    with get_conn() as conn:
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
