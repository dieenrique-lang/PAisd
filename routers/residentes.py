from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import (
    condominio_actual_id,
    no_permisos_response,
    puede_escribir_residentes,
    puede_ver_residentes,
    require_login,
)
from core.database import conectar, obtener_o_crear_departamento
from core.helpers import format_depto, h, render_delete_action
from core.layout import layout


router = APIRouter()


@router.get("/residentes", response_class=HTMLResponse)
def residentes(q: str = Query(default=""), admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_ver_residentes(usuario):
        return no_permisos_response(usuario)
    es_admin = puede_escribir_residentes(usuario)
    condominio_id = condominio_actual_id(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            where_parts = ["r.condominio_id = %s"]
            params = [condominio_id]
            if q:
                like = f"%{q}%"
                where_parts.append(
                    """
                    (
                        r.nombre ILIKE %s OR
                        r.telefono ILIKE %s OR
                        r.email ILIKE %s OR
                        r.tipo ILIKE %s OR
                        COALESCE(d.torre, '') ILIKE %s OR
                        d.numero ILIKE %s OR
                        (COALESCE(d.torre, '') || '-' || d.numero) ILIKE %s
                    )
                    """
                )
                params.extend([like, like, like, like, like, like, like])
            where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            cursor.execute(
                """
                SELECT r.id, r.nombre, r.telefono, r.email, r.tipo, d.torre, d.numero
                FROM residentes r
                LEFT JOIN departamentos d ON r.departamento_id = d.id
                """
                + where_sql
                + """
                ORDER BY r.id DESC
                LIMIT 200
                """,
                params,
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

    form_html = """
    <div class="hero"><h1>Residentes</h1><p>Gestión de residentes.</p></div>
    <div class="card">
        <h2>Agregar residente</h2>
        <form action="/guardar-residente" method="post">
            <label>Nombre residente<input name="nombre" placeholder="Nombre residente" required></label>
            <label>Teléfono<input name="telefono" placeholder="Teléfono"></label>
            <label>Email<input name="email" placeholder="Email"></label>
            <label>Tipo residente<select name="tipo">
                <option value="Propietario">Propietario</option>
                <option value="Arrendatario">Arrendatario</option>
                <option value="Residente">Residente</option>
            </select></label>
            <label>Torre / Block<input name="torre" placeholder="Torre / Block"></label>
            <label>Departamento<input name="numero" placeholder="Departamento" required></label>
            <button class="full" type="submit">Guardar residente</button>
        </form>
    </div>
    <div class="card">
        <h2>Importar residentes desde Excel</h2>
        <p class="muted">Columnas requeridas: nombre, telefono, email, tipo, torre, numero</p>
        <form action="/importar/residentes" method="post" enctype="multipart/form-data">
            <label>Archivo .xlsx<input type="file" name="archivo" accept=".xlsx" required></label>
            <button class="full" type="submit">Importar residentes</button>
        </form>
    </div>
    """ if es_admin else """
    <div class="hero"><h1>Residentes</h1><p>Vista de solo lectura para comité.</p></div>
    """

    contenido = f"""
    {form_html}
    <div class="card">
        <h2>Buscar y filtrar</h2>
        <form action="/residentes" method="get">
            <label>Búsqueda
                <input name="q" value="{h(q)}" placeholder="Buscar por nombre, teléfono, email, tipo o depto">
            </label>
            <button type="submit">Aplicar filtros</button>
            <a class="btn dark" href="/residentes">Limpiar</a>
        </form>
    </div>
    <div class="card">
        <h2>Listado</h2>
        <div class="table-wrap"><table>
            <tr><th>Nombre</th><th>Depto</th><th>Teléfono</th><th>Email</th><th>Tipo</th><th>Acción</th></tr>
            {filas}
        </table></div>
    </div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/dashboard-condominio">Dashboard</a>
        {logout}
    </div>
    """
    return layout("Residentes", contenido, usuario)


@router.post("/guardar-residente")
def guardar_residente(
    admin_session: str | None = Cookie(default=None),
    nombre: str = Form(...),
    telefono: str = Form(""),
    email: str = Form(""),
    tipo: str = Form("Residente"),
    torre: str = Form(""),
    numero: str = Form(...),
):
    usuario = require_login(admin_session)
    if not puede_escribir_residentes(usuario):
        return no_permisos_response(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, condominio_actual_id(usuario), torre, numero)
            cursor.execute(
                """
                INSERT INTO residentes (nombre, telefono, email, tipo, departamento_id, condominio_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (nombre, telefono, email, tipo, dep_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/residentes", status_code=303)


@router.get("/eliminar-residente/{residente_id}")
def eliminar_residente(residente_id: int, admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_escribir_residentes(usuario):
        return no_permisos_response(usuario)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM residentes WHERE id = %s AND condominio_id = %s",
                (residente_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/residentes", status_code=303)

