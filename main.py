from fastapi import Cookie, FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import (
    condominio_actual_id,
    no_permisos_response,
    puede_admin,
    require_login,
)
from core.config import superadmin_configurado
from core import database as database_core
from core.database import conectar
from core.helpers import h
from core.layout import layout
from routers import dashboard, encomiendas, exportar, importar, login, residentes, superadmin, usuarios, vehiculos, visitas

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
app.include_router(superadmin.router)

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









