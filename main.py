from fastapi import FastAPI

from core import database as database_core
from routers import condominios, dashboard, encomiendas, exportar, home, importar, login, residentes, reset, superadmin, usuarios, vehiculos, visitas

app = FastAPI()
app.include_router(home.router)
app.include_router(condominios.router)
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
app.include_router(reset.router)

@app.on_event("startup")
def startup_event():
    try:
        database_core.crear_tablas()
    except Exception as exc:
        print(f"[startup] No se pudieron crear/verificar tablas: {exc}")


@app.get("/health")
def health():
    return {"ok": True}











