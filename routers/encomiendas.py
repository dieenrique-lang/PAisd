from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import (
    condominio_actual_id,
    no_permisos_response,
    puede_escribir_encomiendas,
    puede_exportar,
    require_login,
)
from core.database import conectar, obtener_o_crear_departamento
from core.helpers import ahora_chile, badge_estado, format_depto, h
from core.layout import layout


router = APIRouter()


@router.get("/encomiendas", response_class=HTMLResponse)
def encomiendas(q: str = Query(default=""), solo_pendientes: int = Query(default=0), admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not usuario or usuario.get("rol") not in {"admin", "guardia", "comite"}:
        return no_permisos_response(usuario)
    puede_escribir = puede_escribir_encomiendas(usuario)
    condominio_id = condominio_actual_id(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            where_parts = ["e.condominio_id = %s"]
            params = [condominio_id]
            if q:
                like = f"%{q}%"
                where_parts.append(
                    """
                    (
                        e.nombre_receptor ILIKE %s OR
                        e.descripcion ILIKE %s OR
                        COALESCE(d.torre, '') ILIKE %s OR
                        d.numero ILIKE %s OR
                        (COALESCE(d.torre, '') || '-' || d.numero) ILIKE %s
                    )
                    """
                )
                params.extend([like, like, like, like, like])
            if solo_pendientes:
                where_parts.append("e.entregado = FALSE")

            where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            cursor.execute(
                """
                SELECT e.id, e.nombre_receptor, d.torre, d.numero, e.descripcion, e.recibido_por,
                       e.fecha_recepcion, e.fecha_entrega, e.entregado, e.entregado_a, e.observacion
                FROM encomiendas e
                LEFT JOIN departamentos d ON e.departamento_id = d.id
                """
                + where_sql
                + """
                ORDER BY e.id DESC
                LIMIT 200
                """,
                params,
            )
            data = cursor.fetchall()

    checked = "checked" if solo_pendientes else ""
    filas = ""
    for e in data:
        estado = badge_estado("Entregada", "info") if e[8] else badge_estado("Pendiente", "warning")
        entrega = f"{h(e[7])} - {h(e[9])}" if e[8] else (
            f"""
            <form action="/entregar-encomienda/{e[0]}" method="get" style="display:flex;gap:6px;align-items:center;">
                <input name="entregado_a" placeholder="Entregado a" style="min-width:140px;">
                <button class="btn green" type="submit">Marcar entrega</button>
            </form>
            """
            if puede_escribir
            else badge_estado("Solo lectura", "warning")
        )
        filas += f"""
        <tr>
            <td>{h(e[1])}</td>
            <td>{format_depto(e[2], e[3])}</td>
            <td>{h(e[4])}</td>
            <td>{h(e[5])}</td>
            <td>{h(e[6])}</td>
            <td>{estado}</td>
            <td>{entrega}</td>
            <td>{h(e[10])}</td>
        </tr>
        """

    form_html = """
    <div class="hero"><h1>Encomiendas</h1><p>Gestión de paquetes.</p></div>
    <div class="card">
        <h2>Registrar encomienda</h2>
        <form action="/guardar-encomienda" method="post">
            <label>Nombre receptor<input name="nombre_receptor" placeholder="Nombre receptor" required></label>
            <label>Torre / Block<input name="torre" placeholder="Torre / Block"></label>
            <label>Departamento<input name="numero" placeholder="Departamento" required></label>
            <label>Descripción<input name="descripcion" placeholder="Descripción"></label>
            <label>Recibido por<input name="recibido_por" placeholder="Recibido por (conserje)"></label>
            <label class="full">Observación<textarea name="observacion" placeholder="Observación"></textarea></label>
            <button class="full" type="submit">Guardar encomienda</button>
        </form>
    </div>
    """ if puede_escribir else """
    <div class="hero"><h1>Control de encomiendas</h1><p>Vista en modo lectura.</p></div>
    """

    export_link = '<a class="btn" href="/exportar/encomiendas">Exportar encomiendas</a>' if puede_exportar(usuario) else ""
    contenido = f"""
    {form_html}
    <div class="card">
        <h2>Buscar y filtrar</h2>
        <form action="/encomiendas" method="get">
            <label>Búsqueda<input name="q" value="{h(q)}" placeholder="Buscar por receptor, depto o descripción"></label>
            <label style="display:flex;align-items:center;gap:8px;padding:8px 4px;">
                <input type="checkbox" name="solo_pendientes" value="1" {checked} style="width:auto;">
                Solo pendientes por entregar
            </label>
            <button type="submit">Aplicar filtros</button>
            <a class="btn dark" href="/encomiendas">Limpiar</a>
        </form>
    </div>
    <div class="card">
        <h2>Listado de encomiendas</h2>
        <div class="table-wrap"><table>
            <tr><th>Receptor</th><th>Depto</th><th>Descripción</th><th>Recibido por</th><th>Recepción</th><th>Estado</th><th>Entrega</th><th>Observación</th></tr>
            {filas}
        </table></div>
    </div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/dashboard-condominio">Dashboard</a>
        {export_link}
    </div>
    """
    return layout("Encomiendas", contenido, usuario)


@router.post("/guardar-encomienda")
def guardar_encomienda(
    admin_session: str | None = Cookie(default=None),
    nombre_receptor: str = Form(...),
    torre: str = Form(""),
    numero: str = Form(...),
    descripcion: str = Form(""),
    recibido_por: str = Form(""),
    observacion: str = Form(""),
):
    usuario = require_login(admin_session)
    if not puede_escribir_encomiendas(usuario):
        return no_permisos_response(usuario)
    fecha_recepcion = ahora_chile()
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, condominio_actual_id(usuario), torre, numero)
            cursor.execute(
                """
                INSERT INTO encomiendas (
                    nombre_receptor, departamento_id, descripcion, recibido_por,
                    fecha_recepcion, observacion, condominio_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (nombre_receptor, dep_id, descripcion, recibido_por, fecha_recepcion, observacion, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/encomiendas", status_code=303)


@router.get("/entregar-encomienda/{encomienda_id}")
def entregar_encomienda(encomienda_id: int, entregado_a: str = Query(default=""), admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_escribir_encomiendas(usuario):
        return no_permisos_response(usuario)
    fecha_entrega = ahora_chile()
    entregado_a_value = entregado_a.strip() or "Recibido por residente"
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE encomiendas
                SET entregado = TRUE, fecha_entrega = %s, entregado_a = %s
                WHERE id = %s AND entregado = FALSE AND condominio_id = %s
                """,
                (fecha_entrega, entregado_a_value, encomienda_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/encomiendas", status_code=303)
