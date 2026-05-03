from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import crear_token_sesion, verificar_password
from core.database import get_conn
from core.helpers import h
from core.layout import layout


router = APIRouter()


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


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_form():
    return RedirectResponse(url="/c/demo/login", status_code=303)


@router.get("/c/{slug}/login", response_class=HTMLResponse)
def condominio_login_form(slug: str, msg: str = Query(default="")):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nombre, activo FROM condominios WHERE slug = %s", (slug,))
            condo = cursor.fetchone()
    if not condo or not condo[2]:
        return HTMLResponse("<h3>Condominio no disponible.</h3>", status_code=404)
    return render_login_form(slug, condo[1], msg)


def login_en_condominio(slug: str, username: str, password: str):
    usuario_db = None
    condo = None
    with get_conn() as conn:
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
        login_ok = verificar_password(password, usuario_db[1])
        rol = usuario_db[2]

    if not login_ok:
        return HTMLResponse(f"<h3>Credenciales incorrectas</h3><a href='/c/{h(slug)}/login'>Volver</a>", status_code=401)

    response = RedirectResponse(url="/dashboard-condominio?login=ok&msg=Sesión+iniciada+con+éxito", status_code=303)
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


@router.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    return login_en_condominio("demo", username, password)


@router.post("/c/{slug}/login")
def condominio_login(slug: str, username: str = Form(...), password: str = Form(...)):
    return login_en_condominio(slug, username, password)


@router.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("admin_session")
    return response


@router.get("/c/{slug}/logout")
def condominio_logout(slug: str):
    response = RedirectResponse(url=f"/c/{slug}/login?msg=Sesión+cerrada+correctamente", status_code=303)
    response.delete_cookie("admin_session")
    return response
