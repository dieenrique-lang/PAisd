from fastapi import APIRouter, Cookie
from fastapi.responses import HTMLResponse

from core.auth import condominio_actual_id, no_permisos_response, puede_ver_dashboard, require_login
from core.database import conectar
from core.helpers import ahora_chile, format_depto, h
from core.layout import layout


router = APIRouter()


@router.get("/dashboard-condominio", response_class=HTMLResponse)
def dashboard_condominio(admin_session: str | None = Cookie(default=None)):
    usuario = require_login(admin_session)
    if not puede_ver_dashboard(usuario):
        return no_permisos_response(usuario)
    condominio_id = condominio_actual_id(usuario)
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM residentes WHERE condominio_id = %s", (condominio_id,))
            total_residentes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM vehiculos WHERE condominio_id = %s", (condominio_id,))
            total_vehiculos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM visitas WHERE condominio_id = %s AND DATE(hora_ingreso) = CURRENT_DATE", (condominio_id,))
            visitas_hoy = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM visitas WHERE condominio_id = %s AND hora_salida IS NULL", (condominio_id,))
            visitas_dentro = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM encomiendas WHERE condominio_id = %s AND entregado = FALSE", (condominio_id,))
            encomiendas_pendientes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM encomiendas WHERE condominio_id = %s AND DATE(fecha_recepcion) = CURRENT_DATE", (condominio_id,))
            encomiendas_recibidas_hoy = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM encomiendas WHERE condominio_id = %s AND entregado = TRUE AND DATE(fecha_entrega) = CURRENT_DATE",
                (condominio_id,),
            )
            encomiendas_entregadas_hoy = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT d.torre, d.numero, COUNT(v.id) AS total
                FROM visitas v
                LEFT JOIN departamentos d ON v.departamento_id = d.id
                WHERE v.condominio_id = %s
                GROUP BY d.torre, d.numero
                ORDER BY total DESC
                LIMIT 5
                """,
                (condominio_id,),
            )
            top_deptos = cursor.fetchall()

    top_html = "".join(f"<li>{format_depto(d[0], d[1])}: {d[2]} visitas</li>" for d in top_deptos) or "<li>No hay datos</li>"
    ahora = ahora_chile().strftime("%Y-%m-%d %H:%M")

    contenido = f"""
    <div class="hero"><h1>Dashboard</h1><p>Resumen general del condominio.</p></div>
    <div class="grid">
        <div class="card"><h3><span class="metric-emoji">👥</span> Residentes</h3><div class="stat">{total_residentes}</div></div>
        <div class="card"><h3><span class="metric-emoji">🚗</span> Vehículos</h3><div class="stat">{total_vehiculos}</div></div>
        <div class="card"><h3><span class="metric-emoji">🛂</span> Visitas hoy</h3><div class="stat">{visitas_hoy}</div></div>
        <div class="card"><h3><span class="metric-emoji">🏠</span> Visitas dentro</h3><div class="stat">{visitas_dentro}</div></div>
        <div class="card"><h3><span class="metric-emoji">📦</span> Encomiendas pendientes</h3><div class="stat">{encomiendas_pendientes}</div></div>
        <div class="card"><h3><span class="metric-emoji">📥</span> Recibidas hoy</h3><div class="stat">{encomiendas_recibidas_hoy}</div></div>
        <div class="card"><h3><span class="metric-emoji">✅</span> Entregadas hoy</h3><div class="stat">{encomiendas_entregadas_hoy}</div></div>
    </div>
    <div class="card">
        <h2>Resumen operativo</h2>
        <p class="muted">Visitas activas: {visitas_dentro} · Encomiendas por entregar: {encomiendas_pendientes}.</p>
        <p class="muted">Actualizado: {h(ahora)} (hora local Chile).</p>
    </div>
    <div class="card"><h2>Top departamentos con más visitas</h2><ul>{top_html}</ul><p class="muted">Actualizado: {h(ahora)}</p></div>
    <div class="actions">
        <a class="btn" href="/">Inicio</a>
        <a class="btn" href="/visitas">Control visitas</a>
        <a class="btn" href="/encomiendas">Encomiendas</a>
        <a class="btn" href="/exportar/visitas">Exportar visitas</a>
    </div>
    """
    return layout("Dashboard Condominio", contenido, usuario)
