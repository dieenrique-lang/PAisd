from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
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
        return "Silenciosa o anterior"
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


def mes_nombre(mes):
    nombres = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    return nombres.get(int(mes), f"Mes {mes}")

def dias_para_proximo_cumple(mes, dia):
    hoy = date.today()
    mes = int(mes)
    dia = int(dia)

    cumple_este_anio = date(hoy.year, mes, dia)

    if cumple_este_anio < hoy:
        proximo_cumple = date(hoy.year + 1, mes, dia)
    else:
        proximo_cumple = cumple_este_anio

    return (proximo_cumple - hoy).days


crear_tabla()

def crear_excel_personas(personas, solo_proximos_cumples=False):
    wb = Workbook()
    ws = wb.active
    ws.title = "Personas"

    encabezados = [
        "ID",
        "Nombre",
        "Año",
        "Mes",
        "Día",
        "Edad",
        "Signo",
        "Estación",
        "Generación",
        "Días para próximo cumpleaños"
    ]

    ws.append(encabezados)

    # Estilo encabezado
    fill = PatternFill(fill_type="solid", fgColor="2563EB")
    font = Font(color="FFFFFF", bold=True)
    align = Alignment(horizontal="center", vertical="center")

    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = align

    for persona in personas:
        persona_id, nombre, anio, mes, dia, edad = persona

        dias_faltan = dias_para_proximo_cumple(mes, dia)

        if solo_proximos_cumples and dias_faltan > 7:
            continue

        signo = signo_zodiacal(dia, mes)
        estacion = estacion_sur(dia, mes)
        generacion = generacion_por_anio(anio)

        ws.append([
            persona_id,
            nombre,
            anio,
            mes,
            dia,
            edad,
            signo,
            estacion,
            generacion,
            dias_faltan
        ])

    # Ajuste simple de ancho de columnas
    anchos = {
        "A": 8,
        "B": 24,
        "C": 10,
        "D": 8,
        "E": 8,
        "F": 8,
        "G": 16,
        "H": 14,
        "I": 22,
        "J": 24
    }

    for col, ancho in anchos.items():
        ws.column_dimensions[col].width = ancho

    # Congelar encabezado
    ws.freeze_panes = "A2"

    archivo = BytesIO()
    wb.save(archivo)
    archivo.seek(0)
    return archivo

@app.get("/", response_class=HTMLResponse)
def inicio():
    return """
    <html>
    <head>
    <meta charset="UTF-8">
    <title>Agenda de Personas</title>

    <!-- ICONOS -->
    <script src="https://unpkg.com/lucide@latest"></script>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            margin: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #0f172a, #1d4ed8, #38bdf8, #7c3aed);
            background-size: 300% 300%;
            animation: fondo 12s ease infinite;
        }

        @keyframes fondo {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .card {
            width: 400px;
            padding: 36px;
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(18px);
            box-shadow: 0 25px 60px rgba(0,0,0,0.3);
            text-align: center;
            color: white;
        }

        /* 🔷 HEADER MARCA */
        .brand {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 10px;
        }

        .logo {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .logo i {
            color: white;
        }

        h1 {
            margin: 0;
            font-size: 26px;
        }

        .subtitle {
            font-size: 13px;
            color: rgba(255,255,255,0.8);
            margin-bottom: 20px;
        }

        /* 🔷 INPUTS CON ICONOS */
        .input-group {
            position: relative;
            margin-bottom: 14px;
        }

        .input-group i {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
            width: 18px;
            height: 18px;
        }

        input {
            width: 100%;
            padding: 14px 14px 14px 38px;
            border-radius: 12px;
            border: none;
            outline: none;
            font-size: 14px;
        }

        input:focus {
            box-shadow: 0 0 0 2px #60a5fa;
        }

        /* 🔷 BOTÓN */
        button {
            width: 100%;
            padding: 14px;
            border-radius: 12px;
            border: none;
            font-weight: bold;
            cursor: pointer;
            background: linear-gradient(135deg, #2563eb, #1e40af);
            color: white;
            margin-top: 10px;
            transition: 0.2s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37,99,235,0.4);
        }

        /* 🔷 LINKS */
        .links {
            margin-top: 18px;
            display: grid;
            gap: 10px;
        }

        .link {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px;
            border-radius: 10px;
            background: rgba(255,255,255,0.15);
            text-decoration: none;
            color: white;
            font-weight: bold;
            transition: 0.2s;
        }

        .link:hover {
            background: rgba(255,255,255,0.25);
        }

        .footer {
            margin-top: 15px;
            font-size: 12px;
            color: rgba(255,255,255,0.7);
        }
    </style>
    </head>

    <body>
        <div class="card">

            <!-- 🔷 ENCABEZADO -->
            <div class="brand">
                <div class="logo">
                    <i data-lucide="users"></i>
                </div>
                <h1>PeopleApp</h1>
            </div>

            <div class="subtitle">
                Gestión inteligente de personas + dashboard visual
            </div>

            <!-- 🔷 FORM -->
            <form action="/guardar" method="post">

                <div class="input-group">
                    <i data-lucide="user"></i>
                    <input name="nombre" placeholder="Nombre" required>
                </div>

                <div class="input-group">
                    <i data-lucide="calendar"></i>
                    <input name="anio" type="number" placeholder="Año" required>
                </div>

                <div class="input-group">
                    <i data-lucide="calendar-days"></i>
                    <input name="mes" type="number" placeholder="Mes" min="1" max="12" required>
                </div>

                <div class="input-group">
                    <i data-lucide="calendar-check"></i>
                    <input name="dia" type="number" placeholder="Día" min="1" max="31" required>
                </div>

                <button type="submit">
                    Guardar persona
                </button>
            </form>

            <!-- 🔷 LINKS -->
            <div class="links">
                <a class="link" href="/ver">
                    <i data-lucide="list"></i>
                    Ver personas
                </a>

                <a class="link" href="/dashboard">
                    <i data-lucide="bar-chart-3"></i>
                    Abrir dashboard
                </a>
            </div>

            <div class="footer">
                UI Premium · estilo aplicación real
            </div>
        </div>

        <script>
            lucide.createIcons();
        </script>
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
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial;
            background: #f4f6f8;
            text-align: center;
            margin: 0;
            padding: 30px 15px;
        }
        h2 {
            color: #1d4ed8;
        }
        table {
            margin: 30px auto;
            border-collapse: collapse;
            width: 92%;
            background: white;
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
            border-radius: 14px;
            overflow: hidden;
        }
        th {
            background: #2563eb;
            color: white;
            padding: 14px;
        }
        td {
            padding: 12px 10px;
            border-bottom: 1px solid #e5e7eb;
        }
        tr:hover {
            background-color: #f8fafc;
        }
        a.nombre-link {
            color: #2563eb;
            text-decoration: none;
            font-weight: bold;
        }
        a.nombre-link:hover {
            text-decoration: underline;
        }
        a.eliminar {
            color: #dc2626;
            text-decoration: none;
            font-weight: bold;
            margin-left: 10px;
        }
        a.editar {
            color: #16a34a;
            text-decoration: none;
            font-weight: bold;
            margin-right: 10px;
        }
        a.volver {
            display: block;
            margin-top: 18px;
            color: #2563eb;
            font-weight: bold;
            text-decoration: none;
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
    <a class="volver" href="/dashboard">Ir al dashboard</a>
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
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial;
            background: linear-gradient(135deg, #eef2ff, #f8fafc);
            margin: 0;
            padding: 30px 15px;
            text-align: center;
        }}
        .card {{
            max-width: 780px;
            margin: auto;
            background: white;
            border-radius: 18px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.10);
            padding: 30px;
            text-align: left;
        }}
        h2 {{
            text-align: center;
            color: #2563eb;
            margin-top: 0;
        }}
        .dato {{
            margin: 12px 0;
            font-size: 17px;
            line-height: 1.5;
        }}
        .bloque {{
            margin-top: 26px;
            padding-top: 18px;
            border-top: 1px solid #e5e7eb;
        }}
        a {{
            display: inline-block;
            margin-top: 24px;
            color: #2563eb;
            text-decoration: none;
            font-weight: bold;
        }}
        .nota {{
            color: #64748b;
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
                <div class="dato">• Mes de nacimiento: {mes_nombre(mes)}</div>
                <div class="dato">• Trimestre de nacimiento: {trimestre}</div>
                <div class="dato">• Semestre de nacimiento: {semestre}</div>
            </div>

            <a href="/ver">← Volver al listado</a>
        </div>
    </body>
    </html>
    """

    return html


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, anio, mes, dia, edad
                FROM personas
                ORDER BY id
            """)
            personas = cursor.fetchall()

    total = len(personas)
    edad_promedio = round(sum(p[5] for p in personas) / total, 1) if total > 0 else 0
    edad_max = max((p[5] for p in personas), default=0)
    edad_min = min((p[5] for p in personas), default=0)

    signos = {}
    estaciones = {}
    generaciones = {}
    meses = {i: 0 for i in range(1, 13)}
    proximos_cumples = []

    for persona in personas:
        persona_id, nombre, anio, mes, dia, edad = persona

        signo = signo_zodiacal(dia, mes)
        estacion = estacion_sur(dia, mes)
        generacion = generacion_por_anio(anio)
        dias_faltan = dias_para_proximo_cumple(mes, dia)

        signos[signo] = signos.get(signo, 0) + 1
        estaciones[estacion] = estaciones.get(estacion, 0) + 1
        generaciones[generacion] = generaciones.get(generacion, 0) + 1
        meses[int(mes)] = meses.get(int(mes), 0) + 1

        if dias_faltan <= 7:
            proximos_cumples.append({
                "id": persona_id,
                "nombre": nombre,
                "dia": dia,
                "mes": mes,
                "dias_faltan": dias_faltan
            })

    proximos_cumples.sort(key=lambda x: x["dias_faltan"])

    signos_orden = [
        "Aries", "Tauro", "Géminis", "Cáncer", "Leo", "Virgo",
        "Libra", "Escorpio", "Sagitario", "Capricornio", "Acuario", "Piscis"
    ]
    signos_labels = [s for s in signos_orden if s in signos]
    signos_values = [signos[s] for s in signos_labels]

    estaciones_orden = ["Verano", "Otoño", "Invierno", "Primavera"]
    estaciones_labels = [e for e in estaciones_orden if e in estaciones]
    estaciones_values = [estaciones[e] for e in estaciones_labels]

    generaciones_orden = [
        "Silenciosa o anterior",
        "Baby Boomer",
        "Generación X",
        "Millennial",
        "Generación Z",
        "Generación Alpha"
    ]
    generaciones_labels = [g for g in generaciones_orden if g in generaciones]
    generaciones_values = [generaciones[g] for g in generaciones_labels]

    meses_labels = [mes_nombre(i) for i in range(1, 13)]
    meses_values = [meses[i] for i in range(1, 13)]

    signo_top = max(signos.items(), key=lambda x: x[1])[0] if signos else "-"
    estacion_top = max(estaciones.items(), key=lambda x: x[1])[0] if estaciones else "-"
    generacion_top = max(generaciones.items(), key=lambda x: x[1])[0] if generaciones else "-"

    ranking = sorted(
        [
            ("Signo más frecuente", signo_top, signos.get(signo_top, 0) if signo_top != "-" else 0),
            ("Estación más frecuente", estacion_top, estaciones.get(estacion_top, 0) if estacion_top != "-" else 0),
            ("Generación más frecuente", generacion_top, generaciones.get(generacion_top, 0) if generacion_top != "-" else 0),
        ],
        key=lambda x: x[2],
        reverse=True
    )

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background: linear-gradient(135deg, #eff6ff, #f8fafc);
                color: #1f2937;
            }}
            .wrap {{
                max-width: 1280px;
                margin: 0 auto;
                padding: 28px 18px 40px 18px;
            }}
            .hero {{
                background: linear-gradient(135deg, #2563eb, #1e40af);
                color: white;
                border-radius: 22px;
                padding: 28px;
                box-shadow: 0 18px 40px rgba(37, 99, 235, 0.25);
                margin-bottom: 24px;
            }}
            .hero h1 {{
                margin: 0 0 10px 0;
                font-size: 30px;
            }}
            .hero p {{
                margin: 0;
                opacity: 0.95;
                font-size: 16px;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 18px;
                margin: 24px 0;
            }}
            .stat {{
                background: white;
                border-radius: 18px;
                padding: 22px;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
            }}
            .stat .label {{
                color: #64748b;
                font-size: 14px;
                margin-bottom: 8px;
            }}
            .stat .value {{
                font-size: 30px;
                font-weight: 700;
                color: #2563eb;
            }}
            .alert-panel {{
                background: linear-gradient(135deg, #fff7ed, #fffbeb);
                border: 1px solid #fed7aa;
                border-radius: 18px;
                padding: 20px;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
                margin-bottom: 20px;
            }}
            .alert-panel h3 {{
                margin: 0 0 14px 0;
                color: #c2410c;
                font-size: 20px;
            }}
            .cumple-lista {{
                display: grid;
                gap: 12px;
            }}
            .cumple-item {{
                background: white;
                border-radius: 14px;
                padding: 14px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-left: 6px solid #f59e0b;
            }}
            .cumple-item.hoy {{
                border-left-color: #dc2626;
                background: #fff1f2;
            }}
            .cumple-item .nombre {{
                font-weight: bold;
                color: #111827;
            }}
            .cumple-item .fecha {{
                color: #64748b;
                font-size: 14px;
                margin-top: 4px;
            }}
            .cumple-item .estado {{
                font-weight: bold;
                color: #b45309;
                font-size: 14px;
                text-align: right;
            }}
            .cumple-item.hoy .estado {{
                color: #dc2626;
            }}
            .layout {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 18px;
                align-items: start;
            }}
            .left-column {{
                display: grid;
                gap: 18px;
            }}
            .grid-two {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px;
            }}
            .panel {{
                background: white;
                border-radius: 18px;
                padding: 20px;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
            }}
            .panel h3 {{
                margin: 0 0 16px 0;
                color: #1d4ed8;
                font-size: 19px;
            }}
            .panel canvas {{
                width: 100% !important;
                height: 320px !important;
            }}
            .side-list {{
                margin: 0;
                padding-left: 18px;
            }}
            .side-list li {{
                margin-bottom: 12px;
                line-height: 1.45;
            }}
            .tag {{
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                background: #dbeafe;
                color: #1d4ed8;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .actions {{
                margin-top: 24px;
                text-align: center;
            }}
            .btn {{
                display: inline-block;
                text-decoration: none;
                margin: 8px;
                padding: 12px 18px;
                border-radius: 12px;
                font-weight: bold;
                color: white;
                background: #2563eb;
            }}
            .btn.secondary {{
                background: #0f172a;
            }}
            .mini-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 6px;
            }}
            .mini-table th, .mini-table td {{
                text-align: left;
                padding: 10px 8px;
                border-bottom: 1px solid #e5e7eb;
                font-size: 14px;
            }}
            .mini-table th {{
                color: #64748b;
            }}
            .sin-alertas {{
                color: #78716c;
                background: white;
                border-radius: 14px;
                padding: 14px 16px;
            }}
            @media (max-width: 980px) {{
                .layout {{
                    grid-template-columns: 1fr;
                }}
                .grid-two {{
                    grid-template-columns: 1fr;
                }}
                .cumple-item {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 10px;
                }}
                .cumple-item .estado {{
                    text-align: left;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="wrap">
            <div class="hero">
                <h1>Dashboard de Personas</h1>
                <p>Resumen general de edades, generaciones, signos, estaciones y cumpleaños próximos.</p>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="label">Total de personas</div>
                    <div class="value">{total}</div>
                </div>
                <div class="stat">
                    <div class="label">Edad promedio</div>
                    <div class="value">{edad_promedio}</div>
                </div>
                <div class="stat">
                    <div class="label">Edad mínima</div>
                    <div class="value">{edad_min}</div>
                </div>
                <div class="stat">
                    <div class="label">Edad máxima</div>
                    <div class="value">{edad_max}</div>
                </div>
            </div>

            <div class="alert-panel">
                <h3>🎉 Próximos cumpleaños (7 días)</h3>
                <div class="cumple-lista">
    """

    if proximos_cumples:
        for p in proximos_cumples:
            clase = "cumple-item hoy" if p["dias_faltan"] == 0 else "cumple-item"

            if p["dias_faltan"] == 0:
                estado = "HOY 🎂"
            elif p["dias_faltan"] == 1:
                estado = "Mañana"
            else:
                estado = f"En {p['dias_faltan']} días"

            html += f"""
                    <div class="{clase}">
                        <div>
                            <div class="nombre">
                                <a href="/persona/{p['id']}" style="color: inherit; text-decoration: none;">
                                    {p['nombre']}
                                </a>
                            </div>
                            <div class="fecha">{p['dia']}/{p['mes']}</div>
                        </div>
                        <div class="estado">{estado}</div>
                    </div>
            """
    else:
        html += """
                    <div class="sin-alertas">No hay cumpleaños en los próximos 7 días.</div>
        """

    html += f"""
                </div>
            </div>

            <div class="layout">
                <div class="left-column">
                    <div class="grid-two">
                        <div class="panel">
                            <div class="tag">Distribución</div>
                            <h3>Por signo zodiacal</h3>
                            <canvas id="graficoSignos"></canvas>
                        </div>

                        <div class="panel">
                            <div class="tag">Distribución</div>
                            <h3>Por estación de nacimiento</h3>
                            <canvas id="graficoEstaciones"></canvas>
                        </div>
                    </div>

                    <div class="grid-two">
                        <div class="panel">
                            <div class="tag">Demografía</div>
                            <h3>Por generación</h3>
                            <canvas id="graficoGeneraciones"></canvas>
                        </div>

                        <div class="panel">
                            <div class="tag">Temporal</div>
                            <h3>Por mes de nacimiento</h3>
                            <canvas id="graficoMeses"></canvas>
                        </div>
                    </div>
                </div>

                <div class="right-column">
                    <div class="panel">
                        <div class="tag">Ranking</div>
                        <h3>Indicadores destacados</h3>
                        <table class="mini-table">
                            <thead>
                                <tr>
                                    <th>Categoría</th>
                                    <th>Resultado</th>
                                    <th>Cantidad</th>
                                </tr>
                            </thead>
                            <tbody>
    """

    if ranking:
        for categoria, nombre, cantidad in ranking:
            html += f"""
                                <tr>
                                    <td>{categoria}</td>
                                    <td>{nombre}</td>
                                    <td>{cantidad}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="3">No hay datos</td>
                                </tr>
        """

    html += f"""
                            </tbody>
                        </table>
                    </div>

                    <div class="panel">
                        <div class="tag">Lectura rápida</div>
                        <h3>Resumen útil</h3>
                        <ul class="side-list">
                            <li><strong>Signo dominante:</strong> {signo_top}</li>
                            <li><strong>Estación dominante:</strong> {estacion_top}</li>
                            <li><strong>Generación dominante:</strong> {generacion_top}</li>
                            <li><strong>Cumpleaños próximos:</strong> {len(proximos_cumples)}</li>
                            <li><strong>Base total:</strong> {total} registros</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div class="actions">
                <a class="btn" href="/ver">Ver personas</a>
                <a class="btn secondary" href="/">Volver al inicio</a>
            </div>
        </div>

        <script>
            const signosLabels = {signos_labels};
            const signosValues = {signos_values};

            const estacionesLabels = {estaciones_labels};
            const estacionesValues = {estaciones_values};

            const generacionesLabels = {generaciones_labels};
            const generacionesValues = {generaciones_values};

            const mesesLabels = {meses_labels};
            const mesesValues = {meses_values};

            new Chart(document.getElementById('graficoSignos'), {{
                type: 'pie',
                data: {{
                    labels: signosLabels,
                    datasets: [{{
                        label: 'Cantidad',
                        data: signosValues
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            }});

            new Chart(document.getElementById('graficoEstaciones'), {{
                type: 'doughnut',
                data: {{
                    labels: estacionesLabels,
                    datasets: [{{
                        label: 'Cantidad',
                        data: estacionesValues
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }}
                }}
            }});

            new Chart(document.getElementById('graficoGeneraciones'), {{
                type: 'bar',
                data: {{
                    labels: generacionesLabels,
                    datasets: [{{
                        label: 'Cantidad',
                        data: generacionesValues
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                precision: 0
                            }}
                        }}
                    }}
                }}
            }});

            new Chart(document.getElementById('graficoMeses'), {{
                type: 'line',
                data: {{
                    labels: mesesLabels,
                    datasets: [{{
                        label: 'Nacimientos por mes',
                        data: mesesValues,
                        tension: 0.3,
                        fill: false
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom'
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                precision: 0
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
<div class="actions">
    <a class="btn" href="/ver">Ver personas</a>
    <a class="btn" href="/exportar/excel">Exportar Excel</a>
    <a class="btn" href="/exportar/cumpleanos">Exportar cumpleaños</a>
    <a class="btn secondary" href="/">Volver al inicio</a>
</div>

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
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial;
            background: linear-gradient(135deg, #eef2ff, #f8fafc);
            text-align: center;
            margin: 0;
            padding: 40px 20px;
        }}
        .card {{
            background: white;
            padding: 24px;
            margin: 30px auto;
            width: 340px;
            border-radius: 16px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.10);
        }}
        input {{
            width: 92%;
            padding: 12px;
            margin: 7px;
            border-radius: 10px;
            border: 1px solid #d1d5db;
        }}
        button {{
            background: #16a34a;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            width: 95%;
            font-weight: bold;
        }}
        button:hover {{
            background: #15803d;
        }}
        a {{
            display: block;
            margin-top: 15px;
            color: #2563eb;
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
                <input name="mes" type="number" value="{persona[3]}" min="1" max="12" required><br>
                <input name="dia" type="number" value="{persona[4]}" min="1" max="31" required><br><br>
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
@app.get("/exportar/excel")
def exportar_excel():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, anio, mes, dia, edad
                FROM personas
                ORDER BY id
            """)
            personas = cursor.fetchall()

    archivo = crear_excel_personas(personas)

    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=personas.xlsx"}
    )
@app.get("/exportar/cumpleanos")
def exportar_cumpleanos():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, nombre, anio, mes, dia, edad
                FROM personas
                ORDER BY mes, dia
            """)
            personas = cursor.fetchall()

    archivo = crear_excel_personas(personas, solo_proximos_cumples=True)

    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=proximos_cumpleanos.xlsx"}
    )
