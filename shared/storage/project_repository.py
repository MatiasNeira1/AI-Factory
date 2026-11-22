
from uuid import uuid4

from shared.storage.database import conectar


def crear_proyecto(nombre: str) -> str:
    """Registra un proyecto y devuelve su ID."""

    nombre = nombre.strip()

    if not nombre or len(nombre) > 120:
        raise ValueError(
            "El nombre debe tener entre 1 y 120 caracteres."
        )

    proyecto_id = str(uuid4())

    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, name)
            VALUES (?, ?)
            """,
            (proyecto_id, nombre)
        )

    return proyecto_id


def listar_proyectos() -> list[dict]:
    """Obtiene todos los proyectos."""

    with conectar() as conn:
        rows = conn.execute("""
            SELECT id, name, status,
                   created_at, updated_at
            FROM projects
            ORDER BY updated_at DESC, created_at DESC
        """).fetchall()

    return [dict(row) for row in rows]


def obtener_proyecto(proyecto_id: str):
    """Busca un proyecto por su identificador."""

    with conectar() as conn:
        row = conn.execute(
            """
            SELECT id, name, status,
                   created_at, updated_at
            FROM projects
            WHERE id = ?
            """,
            (proyecto_id,)
        ).fetchone()

    return dict(row) if row else None


def actualizar_estado(proyecto_id: str, estado: str):
    """Actualiza el estado del proyecto."""

    if estado not in ("EN_PROCESO", "APROBADO"):
        raise ValueError("Estado de proyecto inválido.")

    with conectar() as conn:
        cursor = conn.execute(
            """
            UPDATE projects
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (estado, proyecto_id)
        )

        if cursor.rowcount == 0:
            raise ValueError("El proyecto no existe.")
