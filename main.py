from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, date
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


def calcular_dias_vividos(anio, mes, dia):
    nacimiento = date(int(anio), int(mes), int(dia))
    hoy = date.today()
    return (hoy - nacimiento).days


def signo_zodiacal(dia, mes):
    dia = int(dia)
    mes = int(mes)

    if (mes == 3 and dia >= 21) or (mes == 4 and dia <= 19):
        return "Aries"
    elif (mes == 4 and dia >= 20) or (mes == 5 and dia <= 20):
        return "Tauro"
    elif (mes == 5 and dia >= 21) or (mes == 6 and dia <= 20):
        return "Géminis"
    elif (mes == 6 and dia >= 21) or (mes == 7 and dia <= 22):
        return "Cáncer"
    elif (mes == 7 and dia >= 23) or (mes == 8 and dia <= 22):
        return "Leo"
    elif (mes == 8 and dia >= 23) or (mes == 9 and dia <= 22):
        return "Virgo"
    elif (mes == 9 and dia >= 23) or (mes == 10 and dia <= 22):
        return "Libra"
    elif (mes == 10 and dia >= 23) or (mes == 11 and dia <= 21):
        return "Escorpio"
    elif (mes == 11 and dia >= 22) or (mes == 12 and dia <= 21):
        return "Sagitario"
    elif (mes == 12 and dia >= 22) or (mes == 1 and dia <= 19):
        return "Capricornio"
    elif (mes == 1 and dia >= 20) or (mes == 2 and dia <= 18):
        return "Acuario"
    else:
        return "Piscis"


def estacion_sur(dia, mes):
    dia = int(dia)
    mes = int(mes)

    if (mes == 12 and dia >= 21) or mes in [1, 2] or (mes == 3 and dia <= 20):
        return "Verano"
    elif (mes == 3 and dia >= 21) or mes in [4, 5] or (mes == 6 and dia <= 20):
        return "Otoño"
    elif (mes == 6 and dia >= 21) or mes in [7, 8] or (mes == 9 and dia <= 22):
        return "Invierno"
    else:
        return "Primavera"


def personalidad_por_fecha(dia, mes):
    perfiles = {
        1: "Impulso inicial, liderazgo y ganas de empezar cosas.",
        2: "Sensibilidad, cooperación y capacidad de escuchar.",
        3: "Expresión, creatividad y sociabilidad.",
        4: "Orden, constancia y enfoque práctico.",
        5: "Curiosidad, cambio y gusto por la libertad.",
        6: "Responsabilidad, afecto y sentido de protección.",
        7: "Reflexión, análisis e intuición.",
        8: "Ambición, organización y fuerza para avanzar.",
        9: "Generosidad, empatía y visión amplia.",
        10: "Determinación y seguridad personal.",
        11: "Inspiración, intuición y carisma especial.",
        12: "Adaptabilidad y mirada humana.",
        13: "Disciplina y capacidad de reconstruir.",
        14: "Versatilidad y energía cambiante.",
        15: "Encanto, cercanía y magnetismo.",
        16: "Profundidad emocional y autoconocimiento.",
        17: "Perseverancia y orientación al logro.",
        18: "Intensidad, intuición y compromiso.",
        19: "Independencia y brillo personal.",
        20: "Diplomacia, sensibilidad y equilibrio.",
        21: "Creatividad, optimismo y expansión.",
        22: "Visión grande y capacidad de construir.",
        23: "Ingenio, movimiento y adaptabilidad.",
        24: "Calidez, lealtad y sentido familiar.",
        25: "Análisis, observación y búsqueda interna.",
        26: "Responsabilidad, estrategia y foco.",
        27: "Empatía, imaginación y generosidad.",
        28: "Iniciativa, competitividad y energía.",
        29: "Emotividad, intuición y profundidad.",
        30: "Expresividad, humor y creatividad.",
        31: "Estabilidad, esfuerzo y resistencia."
    }

    base = perfiles.get(int(dia), "Personalidad equilibrada y adaptable.")

    extras_mes = {
        1: " Suele haber ambición y deseo de avanzar.",
        2: " Tiende a primar la sensibilidad y el mundo emocional.",
        3: " Hay impulso y energía de inicio.",
        4: " Predomina lo práctico y la necesidad de estructura.",
        5: " Se nota curiosidad y apertura al cambio.",
        6: " Destaca el sentido afectivo y protector.",
        7: " Hay un matiz reflexivo e introspectivo.",
        8: " Se potencia la firmeza y la determinación.",
        9: " Hay vocación humana y amplitud de mirada.",
        10: " Se refuerza la iniciativa y el liderazgo.",
        11: " Aparece un tono intuitivo y creativo.",
        12: " Hay mezcla de sensibilidad y cierre de ciclos."
    }

    return base + extras_mes.get(int(mes), "")


def generacion_por_anio(anio):
    anio = int(anio)
    if anio <= 1945:
        return "Generación Silenciosa o anterior"
    elif anio <= 1964:
        return "Baby Boomer"
    elif anio <= 1980:
        return "Generación X"
    elif anio <= 1996:
        return "Millennial"
    elif anio <= 2012:
        return "Generación Z"
    else:
        return "Generación Alpha"


def trimestre_nacimiento(mes):
    mes = int(mes)
    if mes <= 3:
        return "Primer trimestre"
    elif mes <= 6:
        return "Segundo trimestre"
    elif mes <= 9:
        return "Tercer trimestre"
    return "Cuarto trimestre"


def semestre_nacimiento(mes):
    return "Primer semestre" if int(mes) <= 6 else "Segundo semestre"


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
            width: 88%;
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
        a.nombre-link {
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
        }
        a.nombre-link:hover {
            text-decoration: underline;
        }
        a.eliminar {
            color: red;
            text-decoration: none;
            font-weight: bold;
            margin-left: 10px;
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
            <td><a class="nombre-link" href="/persona/{persona[0]}">{persona[1]}</a></td>
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


@app.get("/persona/{persona_id}", response_class=HTMLResponse)
def detalle_persona(persona_id: int):
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, anio, mes, dia, edad
                FROM personas
                WHERE id = %s
            """, (persona_id,))
            persona = cursor.fetchone()

    if not persona:
        return HTMLResponse("<h2>Persona no encontrada</h2>", status_code=404)

    _, nombre, anio, mes, dia, edad = persona

    dias_vividos = calcular_dias_vividos(anio, mes, dia)
    signo = signo_zodiacal(dia, mes)
    estacion = estacion_sur(dia, mes)
    personalidad = personalidad_por_fecha(dia, mes)
    generacion = generacion_por_anio(anio)
    trimestre = trimestre_nacimiento(mes)
    semestre = semestre_nacimiento(mes)

    html = f"""
    <html>
    <head>
    <style>
        body {{
            font-family: Arial;
            background-color: #f4f6f8;
            margin: 0;
            padding: 30px;
            text-align: center;
        }}
        .card {{
            max-width: 760px;
            margin: auto;
            background: white;
            border-radius: 14px;
            box-shadow: 0 6px 15px rgba(0,0,0,0.1);
            padding: 30px;
            text-align: left;
        }}
        h2 {{
            text-align: center;
            color: #007bff;
        }}
        .dato {{
            margin: 12px 0;
            font-size: 17px;
        }}
        .bloque {{
            margin-top: 24px;
            padding-top: 18px;
            border-top: 1px solid #e5e5e5;
        }}
        a {{
            display: inline-block;
            margin-top: 24px;
            color: #007bff;
            text-decoration: none;
            font-weight: bold;
        }}
        .nota {{
            color: #666;
            font-size: 14px;
            margin-top: 12px;
        }}
    </style>
    </head>
    <body>
        <div class="card">
            <h2>Ficha de {nombre}</h2>

            <div class="dato"><strong>Fecha de nacimiento:</strong> {dia}/{mes}/{anio}</div>
            <div class="dato"><strong>Edad actual:</strong> {edad} años</div>
            <div class="dato"><strong>Días vividos hasta hoy:</strong> {dias_vividos}</div>
            <div class="dato"><strong>Signo zodiacal occidental:</strong> {signo}</div>
            <div class="dato"><strong>Estación del año en que nació:</strong> {estacion}</div>

            <div class="bloque">
                <div class="dato"><strong>Personalidad según día/mes de nacimiento:</strong></div>
                <div class="dato">{personalidad}</div>
                <div class="nota">Esta sección es interpretativa y recreativa, no científica.</div>
            </div>

            <div class="bloque">
                <div class="dato"><strong>Estadísticas demográficas:</strong></div>
                <div class="dato">• Año de nacimiento: {anio}</div>
                <div class="dato">• Generación: {generacion}</div>
                <div class="dato">• Mes de nacimiento: {mes}</div>
                <div class="dato">• Trimestre de nacimiento: {trimestre}</div>
                <div class="dato">• Semestre de nacimiento: {semestre}</div>
            </div>

            <a href="/ver">← Volver al listado</a>
        </div>
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
