from fastapi import APIRouter, Cookie, Query
from fastapi.responses import HTMLResponse

from core.auth import require_login
from core.config import superadmin_configurado
from core.database import get_conn
from core.helpers import h
from core.layout import layout


router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def inicio(msg: str = Query(default=""), admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    superadmin_btn = '<a class="btn dark" href="/superadmin/login">Acceso superadmin</a>' if superadmin_configurado() else ""
    with get_conn() as conn:
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
