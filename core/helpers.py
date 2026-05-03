from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo


def h(value):
    return escape(str(value or ""))


def format_depto(torre, numero):
    if torre and numero:
        return f"{h(torre)}-{h(numero)}"
    return h(torre or numero)


def render_delete_action(es_admin: bool, href: str, confirm_text: str):
    if not es_admin:
        return "<span class='badge warning'>Solo admin</span>"
    return (
        f"<a class='btn red' href='{h(href)}' "
        f"onclick=\"return confirm('{h(confirm_text)}')\">Eliminar</a>"
    )


def ahora_chile() -> datetime:
    return datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)


def badge_estado(texto: str, estilo: str = "neutral"):
    return f"<span class='badge {h(estilo)}'>{h(texto)}</span>"


def encabezados_normalizados(values):
    return [str(v or "").strip().lower() for v in values]
