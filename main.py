from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime
import os
import psycopg

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")


def conectar():
    return psycopg.connect(DATABASE_URL)


def crear_tabla():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    anio INTEGER NOT NULL,
                    mes INTEGER NOT NULL,
                    dia INTEGER NOT NULL,
                    edad INTEGER NOT NULL
                )
            """)
        conn.commit()


def calcular_edad(anio, mes, dia):
    hoy = datetime.now().date()
    edad = hoy.year - int(anio)
    if (hoy.month, hoy.day) < (int(mes), int(dia)):
        edad -= 1
    return edad


crear_tabla()


@app.get("/", response_class=HTMLResponse)
def inicio():
    return """
    <html>
    <head>
    <style>
        body {
            font-family: Arial;
            background-color: #f4f6f8;
            text-align: center;
        }
        .card {
            background: white;
            padding: 20px;
            margin: 50px auto;
            width: 320px;
            border-radius: 12px;
            box-shadow: 0 6px 15px rgba(0,0,0,0.1);
        }
        input {
            width: 90%;
            padding: 10px;
            margin: 6px;
            border-radius: 6px;
            border: 1px solid #ccc;
        }
        button {
            background: #007bff;
            color: white;
            padding: 10px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            width: 95%;
            font-weight: bold;
        }
        button:hover {
            background: #0056b3;
        }
        a {
            display: block;
            margin-top: 15px;
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
        }
    </style>
    </head>
    <body>
        <div class="card">
            <h2>Agenda de Personas</h2>

            <form action="/guardar" method="post">
                <input name="nombre" placeholder="Nombre" required><br>
                <input name="anio" placeholder="Año" type="number" required><br>
                <input name="mes" placeholder="Mes" type="number" required><br>
                <input name="dia" placeholder="Día" type="number" required><br><br>
                <button type="submit">Guardar</button>
            </form>

            <a href="/ver">Ver personas</a>
        </div>
    </body>
    </html>
    """


@app.post("/guardar")
def guardar(
    nombre: str = Form(...),
    anio: int = Form(...),
    mes: int = Form(...),
    dia: int = Form(...)
):
    edad = calcular_edad(anio, mes, dia)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO personas (nombre, anio, mes, dia, edad)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, anio, mes, dia, edad))
        conn.commit()

    return RedirectResponse(url="/ver", status_code=303)


@app.get("/ver", response_class=HTMLResponse)
def ver():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, anio, mes, dia, edad
                FROM personas
                ORDER BY id
            """)
            personas = cursor.fetchall()

    html = """
    <html>
    <head>
    <style>
        body {
            font-family: Arial;
            background-color: #f4f6f8;
            text-align: center;
        }
        table {
            margin: 30px auto;
            border-collapse: collapse;
            width: 85%;
            background: white;
            box-shadow: 0 6px 15px rgba(0,0,0,0.1);
        }
        th {
            background: #007bff;
            color: white;
            padding: 12px;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        a.eliminar {
            color: red;
            text-decoration: none;
            font-weight: bold;
            margin-right: 10px;
        }
        a.editar {
            color: green;
            text-decoration: none;
            font-weight: bold;
            margin-right: 10px;
        }
        a.volver {
            display: block;
            margin-top: 20px;
            color: #007bff;
            font-weight: bold;
        }
    </style>
    </head>
    <body>
    <h2>Listado de Personas</h2>

    <table>
    <tr>
        <th>Nombre</th>
        <th>Edad</th>
        <th>Fecha</th>
        <th>Acción</th>
    </tr>
    """

    for persona in personas:
        html += f"""
        <tr>
            <td>{persona[1]}</td>
            <td>{persona[5]}</td>
            <td>{persona[4]}/{persona[3]}/{persona[2]}</td>
            <td>
                <a class="editar" href="/editar/{persona[0]}">Editar</a>
                <a class="eliminar" href="/eliminar/{persona[0]}"
                onclick="return confirm('¿Seguro que quieres eliminar?')">
                Eliminar
                </a>
            </td>
        </tr>
        """

    html += """
    </table>

    <a class="volver" href="/">Volver</a>
    </body>
    </html>
    """

    return html


@app.get("/editar/{persona_id}", response_class=HTMLResponse)
def editar_form(persona_id: int):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, anio, mes, dia
                FROM personas
                WHERE id = %s
            """, (persona_id,))
            persona = cursor.fetchone()

    if not persona:
        return HTMLResponse("<h2>Persona no encontrada</h2>", status_code=404)

    return f"""
    <html>
    <head>
    <style>
        body {{
            font-family: Arial;
            background-color: #f4f6f8;
            text-align: center;
        }}
        .card {{
            background: white;
            padding: 20px;
            margin: 50px auto;
            width: 320px;
            border-radius: 12px;
            box-shadow: 0 6px 15px rgba(0,0,0,0.1);
        }}
        input {{
            width: 90%;
            padding: 10px;
            margin: 6px;
            border-radius: 6px;
            border: 1px solid #ccc;
        }}
        button {{
            background: #28a745;
            color: white;
            padding: 10px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            width: 95%;
            font-weight: bold;
        }}
        button:hover {{
            background: #1e7e34;
        }}
        a {{
            display: block;
            margin-top: 15px;
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
        }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>Editar Persona</h2>
            <form action="/actualizar/{persona[0]}" method="post">
                <input name="nombre" value="{persona[1]}" required><br>
                <input name="anio" type="number" value="{persona[2]}" required><br>
                <input name="mes" type="number" value="{persona[3]}" required><br>
                <input name="dia" type="number" value="{persona[4]}" required><br><br>
                <button type="submit">Guardar cambios</button>
            </form>
            <a href="/ver">Volver</a>
        </div>
    </body>
    </html>
    """


@app.post("/actualizar/{persona_id}")
def actualizar(
    persona_id: int,
    nombre: str = Form(...),
    anio: int = Form(...),
    mes: int = Form(...),
    dia: int = Form(...)
):
    edad = calcular_edad(anio, mes, dia)

    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE personas
                SET nombre = %s, anio = %s, mes = %s, dia = %s, edad = %s
                WHERE id = %s
            """, (nombre, anio, mes, dia, edad, persona_id))
        conn.commit()

    return RedirectResponse(url="/ver", status_code=303)


@app.get("/eliminar/{persona_id}")
def eliminar(persona_id: int):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM personas WHERE id = %s", (persona_id,))
        conn.commit()

    return RedirectResponse(url="/ver", status_code=303)
