from fastapi import APIRouter, Cookie, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from core.auth import (
    condominio_actual_id,
    no_permisos_response,
    puede_escribir_visitas,
    puede_exportar,
    require_login,
)
from core.database import conectar, obtener_o_crear_departamento
from core.helpers import ahora_chile, badge_estado, format_depto, h
from core.layout import layout


router = APIRouter()


@router.get("/visitas", response_class=HTMLResponse)
def visitas(q: str = Query(default=""), solo_dentro: int = Query(default=0), admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not usuario or usuario.get("rol") not in {"admin", "guardia", "comite"}:
        return no_permisos_response(usuario)
    puede_escribir = puede_escribir_visitas(usuario)
    condominio_id = condominio_actual_id(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            where_parts = ["v.condominio_id = %s"]
            params = [condominio_id]
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
        estado = badge_estado("Dentro", "success") if v[9] is None else badge_estado("Salió", "dark")
        salida = (
            f"<a class='btn green' href='/salida-visita/{v[0]}'>Marcar salida</a>"
            if v[9] is None and puede_escribir
            else (h(v[9]) if v[9] is not None else badge_estado("Solo lectura", "warning"))
        )
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
    form_html = """
    <div class="hero"><h1>Control de visitas</h1><p>Control de accesos.</p></div>
    <div class="card">
        <h2>Registrar ingreso</h2>
        <form action="/guardar-visita" method="post">
            <label>Nombre visita<input name="nombre" placeholder="Nombre visita" required></label>
            <label>RUT / Documento<input name="rut" placeholder="RUT / Documento"></label>
            <label>Patente (opcional)<input name="patente" placeholder="Patente vehículo (opcional)"></label>
            <label>Torre / Block<input name="torre" placeholder="Torre / Block"></label>
            <label>Departamento que visita<input name="numero" placeholder="Departamento que visita" required></label>
            <label>Autorizado por<input name="autorizado_por" placeholder="Autorizado por"></label>
            <label class="full">Observación<textarea name="observacion" placeholder="Observación"></textarea></label>
            <button class="full" type="submit">Registrar ingreso</button>
        </form>
    </div>
    """ if puede_escribir else """
    <div class="hero"><h1>Control de visitas</h1><p>Vista en modo lectura.</p></div>
    """

    export_link = '<a class="btn" href="/exportar/visitas">Exportar visitas</a>' if puede_exportar(usuario) else ""
    contenido = f"""
    {form_html}
    <div class="card">
        <h2>Buscar y filtrar</h2>
        <form action="/visitas" method="get">
            <label>Búsqueda<input name="q" value="{h(q)}" placeholder="Buscar por nombre, RUT, patente o depto"></label>
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
        <div class="table-wrap"><table>
            <tr><th>Visita</th><th>RUT</th><th>Patente</th><th>Depto</th><th>Autoriza</th><th>Ingreso</th><th>Estado</th><th>Salida</th></tr>
            {filas}
        </table></div>
    </div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        {export_link}
    </div>
    """
    return layout("Visitas", contenido, usuario)


@router.post("/guardar-visita")
def guardar_visita(
    admin_session: str | None = Cookie(default=None),
    nombre: str = Form(...),
    rut: str = Form(""),
    patente: str = Form(""),
    torre: str = Form(""),
    numero: str = Form(...),
    autorizado_por: str = Form(""),
    observacion: str = Form(""),
):
    usuario = require_login(admin_session)
    if not puede_escribir_visitas(usuario):
        return no_permisos_response(usuario)
    hora_ingreso = ahora_chile()
    with conectar() as conn:
        with conn.cursor() as cursor:
            dep_id = obtener_o_crear_departamento(cursor, condominio_actual_id(usuario), torre, numero)
            cursor.execute(
                """
                INSERT INTO visitas (nombre, rut, patente, departamento_id, autorizado_por, observacion, hora_ingreso, condominio_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (nombre, rut, patente.upper(), dep_id, autorizado_por, observacion, hora_ingreso, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/visitas", status_code=303)


@router.get("/salida-visita/{visita_id}")
def salida_visita(visita_id: int, admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_escribir_visitas(usuario):
        return no_permisos_response(usuario)
    hora_salida = ahora_chile()
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE visitas
                SET hora_salida = %s
                WHERE id = %s AND hora_salida IS NULL AND condominio_id = %s
                """,
                (hora_salida, visita_id, condominio_actual_id(usuario)),
            )
        conn.commit()
    return RedirectResponse(url="/visitas", status_code=303)
