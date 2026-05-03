from fastapi.responses import HTMLResponse

from core.config import superadmin_configurado
from core.helpers import h


def layout(titulo: str, contenido: str, usuario=None):
    usuario_label = "Sesión invitado"
    usuario_badge = "badge dark"
    condominio_label = "Sin condominio"
    admin_link = ""
    superadmin_link = '<a href="/superadmin/login">🛡️ Superadmin</a>' if superadmin_configurado() else ""
    account_links = ""
    if usuario:
        usuario_label = f"{h(usuario.get('username'))} · {h(usuario.get('rol'))}"
        condominio_label = h(usuario.get("condominio_nombre") or "Condominio")
        usuario_badge = "badge info"
        if usuario.get("rol") == "admin":
            admin_link = '<a href="/admin/usuarios">👤 Usuarios</a><a href="/admin/restablecer">🧨 Restablecer datos</a>'
        if usuario.get("rol") == "superadmin":
            admin_link += '<a href="/superadmin">🛡️ Superadmin</a>'
            account_links = '<a class="btn dark" href="/superadmin/logout">Cerrar sesión</a>'
        else:
            slug = h(usuario.get("condominio_slug") or "demo")
            account_links = f'<a class="btn" href="/c/{slug}/mi-cuenta">Mi cuenta</a><a class="btn dark" href="/c/{slug}/logout">Cerrar sesión</a>'
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{h(titulo)}</title>
        <style>
            :root {{
                --bg:#f1f5f9;
                --surface:#ffffff;
                --text:#0f172a;
                --muted:#64748b;
                --primary:#1d4ed8;
                --primary-dark:#1e3a8a;
                --danger:#dc2626;
                --success:#16a34a;
                --border:#dbe2ea;
                --shadow:0 10px 28px rgba(15,23,42,.08);
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                background: var(--bg);
                margin: 0;
                color: var(--text);
            }}
            .app-layout {{
                display: grid;
                grid-template-columns: 260px 1fr;
                min-height: 100vh;
            }}
            .sidebar {{
                background: #0f172a;
                color: #e2e8f0;
                padding: 24px 16px;
                position: sticky;
                top: 0;
                height: 100vh;
            }}
            .logo {{
                display:flex;
                align-items:center;
                gap:10px;
                margin-bottom: 18px;
            }}
            .logo-icon {{
                width: 34px;
                height: 34px;
                border-radius: 10px;
                background: linear-gradient(145deg, #2563eb, #1e40af);
                display:flex;
                align-items:center;
                justify-content:center;
                font-size: 1.05rem;
                box-shadow: 0 8px 16px rgba(37,99,235,.3);
            }}
            .logo-text {{ font-size: 1.1rem; font-weight: 800; color: #fff; letter-spacing:.01em; }}
            .sidebar a {{
                display: block;
                padding: 10px 12px;
                border-radius: 10px;
                color: #cbd5e1;
                text-decoration: none;
                margin-bottom: 8px;
                font-weight: 600;
            }}
            .sidebar a:hover {{ background: #1e293b; color: #fff; }}
            .content-area {{ padding: 20px; }}
            .topbar {{
                background: #fff;
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 14px 18px;
                margin-bottom: 18px;
                display:flex;
                align-items:center;
                justify-content:space-between;
                box-shadow: var(--shadow);
            }}
            .wrap {{ max-width: 1200px; margin: 0 auto; }}
            .hero {{
                background: linear-gradient(125deg,var(--primary),var(--primary-dark));
                color: white;
                padding: 28px;
                border-radius: 18px;
                margin-bottom: 20px;
                box-shadow: var(--shadow);
            }}
            .hero h1 {{ margin: 0 0 6px; }}
            .hero p {{ margin: 0; opacity: .92; }}
            .card {{
                background: var(--surface);
                border: 1px solid var(--border);
                padding: 22px;
                border-radius: 16px;
                box-shadow: var(--shadow);
                margin-bottom: 18px;
            }}
            .actions {{ display:flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
            form {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap: 10px; }}
            form .full {{ grid-column: 1/-1; }}
            input, select, textarea {{
                width: 100%;
                padding: 10px 12px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                outline: none;
                font-size: .95rem;
            }}
            input:focus, select:focus, textarea:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,.15); }}
            button, .btn {{
                display:inline-flex;
                align-items:center;
                justify-content:center;
                background: var(--primary);
                color:#fff;
                border:none;
                border-radius: 10px;
                text-decoration:none;
                padding: 9px 14px;
                font-weight: 600;
                cursor:pointer;
            }}
            .btn.dark {{ background:#0f172a; }}
            .btn.red {{ background: var(--danger); }}
            .btn.green {{ background: var(--success); }}
            .muted {{ color: var(--muted); font-weight: 600; }}
            .table-wrap {{ overflow-x:auto; border: 1px solid var(--border); border-radius: 14px; }}
            table {{ width:100%; border-collapse: separate; border-spacing: 0; min-width: 760px; }}
            th {{ background: #e2e8f0; color: #1e293b; text-align:left; padding: 12px; font-size:.84rem; text-transform: uppercase; letter-spacing: .03em; }}
            td {{ background:#fff; padding: 10px 11px; border-top: 1px solid var(--border); vertical-align: top; }}
            tr:hover td {{ background: #f8fafc; }}
            .badge {{
                display:inline-flex;
                align-items:center;
                padding:4px 10px;
                border-radius: 999px;
                font-size: .76rem;
                font-weight: 700;
            }}
            .badge.success {{ background:#dcfce7; color:#166534; }}
            .badge.warning {{ background:#fef3c7; color:#92400e; }}
            .badge.info {{ background:#dbeafe; color:#1e40af; }}
            .badge.dark {{ background:#e2e8f0; color:#0f172a; }}
            .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 14px; }}
            .stat {{ font-size: 2rem; font-weight: 800; color: var(--primary); }}
            .metric-emoji {{ font-size: 1.3rem; }}
            label {{ font-weight: 600; color:#334155; display:flex; flex-direction:column; gap:6px; }}
            @media (max-width: 980px) {{
                .app-layout {{ grid-template-columns: 1fr; }}
                .sidebar {{ position: static; height: auto; }}
                .content-area {{ padding: 14px; }}
            }}
        </style>
    </head>
    <body>
        <div class="app-layout">
            <aside class="sidebar">
                <div class="logo">
                    <div class="logo-icon">🏢</div>
                    <div class="logo-text">CondoControl<br><small style="font-size:12px;color:#94a3b8;">{condominio_label}</small></div>
                </div>
                <a href="/dashboard-condominio">📊 Dashboard</a>
                <a href="/residentes">👥 Residentes</a>
                <a href="/vehiculos">🚗 Vehículos</a>
                <a href="/visitas">🛂 Visitas</a>
                <a href="/encomiendas">📦 Encomiendas</a>
                {admin_link}
                {superadmin_link}
            </aside>
            <main class="content-area">
                <div class="wrap">
                    <div class="topbar">
                        <div>
                            <strong>{h(titulo)}</strong>
                            <div class="muted" style="font-size:12px;">
                                Condominio: {h(usuario.get("condominio_nombre") if usuario else "No autenticado")} ·
                                Usuario: {h(usuario.get("username") if usuario else "-")} ·
                                Rol: {h(usuario.get("rol") if usuario else "-")}
                            </div>
                        </div>
                        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
                            <span id="admin-status" class="{usuario_badge}">{usuario_label}</span>
                            {account_links}
                        </div>
                    </div>
                    {contenido}
                </div>
            </main>
        </div>
    </body>
    </html>
    """


def render_resultado_importacion(titulo: str, volver_url: str, importados: int, omitidos: int, errores: list[str], usuario):
    errores_html = ""
    if errores:
        items = "".join(f"<li>{h(e)}</li>" for e in errores[:80])
        extra = f"<p class='muted'>Mostrando 80 de {len(errores)} errores.</p>" if len(errores) > 80 else ""
        errores_html = f"<h3>Errores</h3><ul>{items}</ul>{extra}"
    contenido = f"""
    <div class="hero"><h1>Importación completada</h1><p>Resultado del proceso de carga masiva.</p></div>
    <div class="card">
        <h2>{h(titulo)}</h2>
        <p><strong>{importados}</strong> registros importados.</p>
        <p><strong>{omitidos}</strong> filas omitidas.</p>
        {errores_html}
        <div class="actions">
            <a class="btn" href="{h(volver_url)}">Volver</a>
        </div>
    </div>
    """
    return HTMLResponse(layout("Importación", contenido, usuario))
