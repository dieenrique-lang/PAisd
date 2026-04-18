from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from openpyxl import Workbook, load_workbook
from datetime import datetime
import os

app = FastAPI()

archivo = "personas.xlsx"

# Crear Excel si no existe
if not os.path.exists(archivo):
    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre", "Año", "Mes", "Día", "Edad"])
    wb.save(archivo)

# Calcular edad
def calcular_edad(anio, mes, dia):
    hoy = datetime.now().date()
    edad = hoy.year - int(anio)
    if (hoy.month, hoy.day) < (int(mes), int(dia)):
        edad -= 1
    return edad

# Página principal
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
                <input name="nombre" placeholder="Nombre"><br>
                <input name="anio" placeholder="Año"><br>
                <input name="mes" placeholder="Mes"><br>
                <input name="dia" placeholder="Día"><br><br>
                <button type="submit">Guardar</button>
            </form>

            <a href="/ver">Ver personas</a>
        </div>
    </body>
    </html>
    """

# Guardar persona
@app.post("/guardar")
def guardar(nombre: str = Form(...), anio: int = Form(...), mes: int = Form(...), dia: int = Form(...)):
    wb = load_workbook(archivo)
    ws = wb.active

    edad = calcular_edad(anio, mes, dia)

    ws.append([nombre, anio, mes, dia, edad])
    wb.save(archivo)

    return RedirectResponse(url="/ver", status_code=303)

# Ver personas
@app.get("/ver", response_class=HTMLResponse)
def ver():
    wb = load_workbook(archivo)
    ws = wb.active

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
            width: 80%;
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

    fila_num = 2
    for fila in ws.iter_rows(min_row=2, values_only=True):
        html += f"""
        <tr>
            <td>{fila[0]}</td>
            <td>{fila[4]}</td>
            <td>{fila[3]}/{fila[2]}/{fila[1]}</td>
            <td>
                <a class="eliminar" href="/eliminar/{fila_num}" 
                onclick="return confirm('¿Seguro que quieres eliminar?')">
                Eliminar
                </a>
            </td>
        </tr>
        """
        fila_num += 1

    html += """
    </table>

    <a class="volver" href="/">Volver</a>
    </body>
    </html>
    """

    return html

# Eliminar persona
@app.get("/eliminar/{fila}")
def eliminar(fila: int):
    wb = load_workbook(archivo)
    ws = wb.active

    ws.delete_rows(fila)
    wb.save(archivo)

    return RedirectResponse(url="/ver", status_code=303)