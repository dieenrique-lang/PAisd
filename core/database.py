import psycopg

from core.config import ADMIN_PASSWORD_HASH, ADMIN_USERNAME, DATABASE_URL


def conectar():
    return psycopg.connect(DATABASE_URL)


def get_conn():
    return conectar()


def crear_tablas():
    with conectar() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS condominios (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    activo BOOLEAN DEFAULT TRUE,
                    creado_en TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS departamentos (
                    id SERIAL PRIMARY KEY,
                    torre TEXT,
                    numero TEXT NOT NULL
                )
                """
            )
            cursor.execute("ALTER TABLE departamentos ADD COLUMN IF NOT EXISTS condominio_id INTEGER REFERENCES condominios(id)")
            cursor.execute("ALTER TABLE departamentos DROP CONSTRAINT IF EXISTS departamentos_torre_numero_key")
            cursor.execute("DROP INDEX IF EXISTS ux_departamentos_condominio_torre_numero")
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'uq_departamentos_condominio_torre_numero'
                    ) THEN
                        ALTER TABLE departamentos
                        ADD CONSTRAINT uq_departamentos_condominio_torre_numero
                        UNIQUE (condominio_id, torre, numero);
                    END IF;
                END
                $$;
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS residentes (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    telefono TEXT,
                    email TEXT,
                    tipo TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id)
                )
                """
            )
            cursor.execute("ALTER TABLE residentes ADD COLUMN IF NOT EXISTS condominio_id INTEGER REFERENCES condominios(id)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vehiculos (
                    id SERIAL PRIMARY KEY,
                    patente TEXT NOT NULL,
                    marca TEXT,
                    modelo TEXT,
                    color TEXT,
                    estacionamiento TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id)
                )
                """
            )
            cursor.execute("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS estacionamiento TEXT")
            cursor.execute("ALTER TABLE vehiculos ADD COLUMN IF NOT EXISTS condominio_id INTEGER REFERENCES condominios(id)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS visitas (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    rut TEXT,
                    patente TEXT,
                    departamento_id INTEGER REFERENCES departamentos(id),
                    autorizado_por TEXT,
                    observacion TEXT,
                    hora_ingreso TIMESTAMP DEFAULT NOW(),
                    hora_salida TIMESTAMP
                )
                """
            )
            cursor.execute("ALTER TABLE visitas ADD COLUMN IF NOT EXISTS patente TEXT")
            cursor.execute("ALTER TABLE visitas ADD COLUMN IF NOT EXISTS condominio_id INTEGER REFERENCES condominios(id)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS encomiendas (
                    id SERIAL PRIMARY KEY,
                    nombre_receptor TEXT NOT NULL,
                    departamento_id INTEGER REFERENCES departamentos(id),
                    descripcion TEXT,
                    recibido_por TEXT,
                    fecha_recepcion TIMESTAMP NOT NULL,
                    fecha_entrega TIMESTAMP,
                    entregado BOOLEAN NOT NULL DEFAULT FALSE,
                    entregado_a TEXT,
                    observacion TEXT
                )
                """
            )
            cursor.execute("ALTER TABLE encomiendas ADD COLUMN IF NOT EXISTS condominio_id INTEGER REFERENCES condominios(id)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    rol TEXT NOT NULL,
                    activo BOOLEAN DEFAULT TRUE,
                    creado_en TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS condominio_id INTEGER REFERENCES condominios(id)")
            cursor.execute("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_username_key")
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_condominio_username
                ON usuarios (condominio_id, username)
                """
            )

            cursor.execute("SELECT id FROM condominios WHERE slug = 'demo'")
            demo = cursor.fetchone()
            if demo:
                demo_id = demo[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO condominios (nombre, slug, activo)
                    VALUES (%s, %s, TRUE)
                    RETURNING id
                    """,
                    ("Condominio Demo", "demo"),
                )
                demo_id = cursor.fetchone()[0]

            cursor.execute("UPDATE departamentos SET condominio_id = %s WHERE condominio_id IS NULL", (demo_id,))
            cursor.execute("UPDATE residentes SET condominio_id = %s WHERE condominio_id IS NULL", (demo_id,))
            cursor.execute("UPDATE vehiculos SET condominio_id = %s WHERE condominio_id IS NULL", (demo_id,))
            cursor.execute("UPDATE visitas SET condominio_id = %s WHERE condominio_id IS NULL", (demo_id,))
            cursor.execute("UPDATE encomiendas SET condominio_id = %s WHERE condominio_id IS NULL", (demo_id,))
            cursor.execute("UPDATE usuarios SET condominio_id = %s WHERE condominio_id IS NULL", (demo_id,))

            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE condominio_id = %s", (demo_id,))
            total_usuarios = cursor.fetchone()[0]
            if total_usuarios == 0 and ADMIN_PASSWORD_HASH:
                cursor.execute(
                    """
                    INSERT INTO usuarios (username, password_hash, rol, activo, condominio_id)
                    VALUES (%s, %s, %s, TRUE, %s)
                    ON CONFLICT (condominio_id, username) DO NOTHING
                    """,
                    (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, "admin", demo_id),
                )
        conn.commit()


def obtener_o_crear_departamento(cursor, condominio_id, torre, numero):
    cursor.execute(
        """
        SELECT id FROM departamentos
        WHERE condominio_id = %s
          AND torre = %s
          AND numero = %s
        """,
        (condominio_id, torre, numero),
    )
    dep = cursor.fetchone()
    if dep:
        return dep[0]

    cursor.execute(
        """
        INSERT INTO departamentos (torre, numero, condominio_id)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (torre, numero, condominio_id),
    )
    return cursor.fetchone()[0]
