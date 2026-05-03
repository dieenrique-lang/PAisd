import bcrypt
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer

from core.config import ADMIN_PASSWORD_HASH, SECRET_KEY, SUPERADMIN_PASSWORD_HASH
from core.layout import layout


serializer = URLSafeSerializer(SECRET_KEY, salt="admin-session")


def crear_token_sesion(
    username: str,
    rol: str,
    condominio_id: int | None = None,
    condominio_nombre: str = "",
    condominio_slug: str = "",
):
    payload = {"username": username, "rol": rol}
    if condominio_id is not None:
        payload.update(
            {
                "condominio_id": condominio_id,
                "condominio_nombre": condominio_nombre,
                "condominio_slug": condominio_slug,
            }
        )
    return serializer.dumps(payload)


def require_login(token: str | None):
    if not token:
        return None
    try:
        data = serializer.loads(token)
        username = data.get("username")
        rol = data.get("rol")
        condominio_id = data.get("condominio_id")
        condominio_nombre = data.get("condominio_nombre")
        condominio_slug = data.get("condominio_slug")
        if username and rol == "superadmin":
            return {"username": username, "rol": "superadmin"}
        if username and rol and condominio_id:
            return {
                "username": username,
                "rol": rol,
                "condominio_id": condominio_id,
                "condominio_nombre": condominio_nombre or "",
                "condominio_slug": condominio_slug or "demo",
            }
    except BadSignature:
        return None
    return None


def verificar_password_admin(password: str):
    if not ADMIN_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))


def verificar_password_superadmin(password: str):
    if not SUPERADMIN_PASSWORD_HASH:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), SUPERADMIN_PASSWORD_HASH.encode("utf-8"))


def verificar_password(password: str, password_hash: str):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def hash_password(password: str):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def puede_admin(usuario):
    return bool(usuario and usuario.get("rol") == "admin")


def puede_superadmin(usuario):
    return bool(usuario and usuario.get("rol") == "superadmin")


def puede_guardia(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "guardia"})


def puede_comite(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "comite"})


def puede_ver_dashboard(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "guardia", "comite"})


def puede_ver_residentes(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "guardia", "comite"})


def puede_ver_vehiculos(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "guardia", "comite"})


def puede_escribir_residentes(usuario):
    return bool(usuario and usuario.get("rol") == "admin")


def puede_escribir_vehiculos(usuario):
    return bool(usuario and usuario.get("rol") == "admin")


def puede_exportar(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "comite"})


def puede_escribir_visitas(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "guardia"})


def puede_escribir_encomiendas(usuario):
    return bool(usuario and usuario.get("rol") in {"admin", "guardia"})


def no_permisos_response(usuario):
    if not usuario:
        return RedirectResponse(url="/admin/login", status_code=303)
    contenido = """
    <div class="card">
        <h2>No tienes permisos para esta acción</h2>
        <p class="muted">Tu rol actual no permite ejecutar esta operación.</p>
        <div class="actions"><a class="btn" href="/">Volver al inicio</a></div>
    </div>
    """
    return HTMLResponse(layout("Sin permisos", contenido, usuario))


def condominio_actual_id(usuario):
    return int(usuario.get("condominio_id", 0)) if usuario else 0
