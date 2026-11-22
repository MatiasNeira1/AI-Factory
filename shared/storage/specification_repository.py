#Este módulo administrará las versiones sin comunicarse con Groq.
import json
from pathlib import Path

from shared.config import BASE_DIR
from agents.architect.validator import validar_especificacion
from shared.storage.database import conectar


def registrar_propuesta(proyecto_id: str, data: dict) -> int:
    """
    Guarda una nueva versión pendiente de revisión.

    También guarda la respuesta del agente en el
    historial, dentro de la misma transacción.
    """

    if data.get("estado") != "REVISAR":
        raise ValueError(
            "Solo se versionan propuestas en estado REVISAR."
        )

    validar_especificacion(data)

    contenido = json.dumps(data, ensure_ascii=False)

    with conectar() as conn:
        # Bloquea escrituras concurrentes mientras
        # asignamos el siguiente número de versión.
        conn.execute("BEGIN IMMEDIATE")

        proyecto = conn.execute(
            "SELECT id FROM projects WHERE id = ?",
            (proyecto_id,)
        ).fetchone()

        if proyecto is None:
            raise ValueError("El proyecto no existe.")

        fila = conn.execute("""
            SELECT COALESCE(MAX(version), 0) + 1
            FROM specifications
            WHERE project_id = ?
        """, (proyecto_id,)).fetchone()

        nueva_version = fila[0]

        # Una propuesta pendiente anterior queda
        # sustituida, pero no se elimina.
        conn.execute("""
            UPDATE specifications
            SET status = 'SUSTITUIDA'
            WHERE project_id = ?
              AND status = 'EN_REVISION'
        """, (proyecto_id,))

        conn.execute("""
            INSERT INTO specifications (
                project_id, version, status, content
            )
            VALUES (?, ?, 'EN_REVISION', ?)
        """, (
            proyecto_id,
            nueva_version,
            contenido,
        ))

        # Guardamos también el mensaje del Arquitecto.
        conn.execute("""
            INSERT INTO messages (
                project_id, role, content
            )
            VALUES (?, 'assistant', ?)
        """, (proyecto_id, contenido))

        conn.execute("""
            UPDATE projects
            SET status = 'EN_PROCESO',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (proyecto_id,))

    return nueva_version


def listar_versiones(proyecto_id: str) -> list[dict]:
    """Lista el historial de versiones."""

    with conectar() as conn:
        filas = conn.execute("""
            SELECT version, status, created_at, approved_at
            FROM specifications
            WHERE project_id = ?
            ORDER BY version DESC
        """, (proyecto_id,)).fetchall()

    return [dict(fila) for fila in filas]


def obtener_version(proyecto_id: str, version: int):
    """Recupera una versión y su contenido JSON."""

    with conectar() as conn:
        fila = conn.execute("""
            SELECT version, status, content,
                   created_at, approved_at
            FROM specifications
            WHERE project_id = ?
              AND version = ?
        """, (proyecto_id, version)).fetchone()

    if fila is None:
        return None

    resultado = dict(fila)
    resultado["contenido"] = json.loads(
        resultado.pop("content")
    )

    return resultado


def obtener_ultima_version(proyecto_id: str):
    """Devuelve la versión más reciente del proyecto."""

    with conectar() as conn:
        fila = conn.execute("""
            SELECT MAX(version)
            FROM specifications
            WHERE project_id = ?
        """, (proyecto_id,)).fetchone()

    if fila is None or fila[0] is None:
        return None

    return obtener_version(proyecto_id, fila[0])

def aprobar_version(proyecto_id: str, version: int):
    """Aprueba la versión más reciente del proyecto."""

    with conectar() as conn:
        conn.execute("BEGIN IMMEDIATE")

        fila = conn.execute("""
            SELECT version, status
            FROM specifications
            WHERE project_id = ?
              AND version = ?
        """, (proyecto_id, version)).fetchone()

        if fila is None:
            raise ValueError("La versión no existe.")

        ultima = conn.execute("""
            SELECT MAX(version)
            FROM specifications
            WHERE project_id = ?
        """, (proyecto_id,)).fetchone()[0]

        if version != ultima:
            raise ValueError(
                "Solo puedes aprobar la última versión."
            )

        if fila["status"] != "EN_REVISION":
            raise ValueError(
                "La versión no está pendiente de aprobación."
            )

        conn.execute("""
            UPDATE specifications
            SET status = 'APROBADA',
                approved_at = CURRENT_TIMESTAMP
            WHERE project_id = ?
              AND version = ?
        """, (proyecto_id, version))

        conn.execute("""
            UPDATE projects
            SET status = 'APROBADO',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (proyecto_id,))


def solicitar_revision(proyecto_id: str, cambios: str):
    """
    Permite solicitar cambios después de aprobar
    una arquitectura.
    """

    cambios = cambios.strip()

    if not cambios:
        raise ValueError(
            "Debes describir los cambios solicitados."
        )

    with conectar() as conn:
        conn.execute("BEGIN IMMEDIATE")

        proyecto = conn.execute("""
            SELECT status
            FROM projects
            WHERE id = ?
        """, (proyecto_id,)).fetchone()

        if proyecto is None:
            raise ValueError("El proyecto no existe.")

        if proyecto["status"] != "APROBADO":
            raise ValueError(
                "El proyecto todavía no está aprobado."
            )

        mensaje = (
            "Solicito una nueva revisión de la "
            "arquitectura aprobada. Cambios: "
            + cambios
        )

        conn.execute("""
            INSERT INTO messages (
                project_id, role, content
            )
            VALUES (?, 'user', ?)
        """, (proyecto_id, mensaje))

        conn.execute("""
            UPDATE projects
            SET status = 'EN_PROCESO',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (proyecto_id,))



def comparar_versiones(
    proyecto_id: str,
    version_a: int,
    version_b: int,
):
    """Compara elementos estructurados por ID."""

    anterior = obtener_version(proyecto_id, version_a)
    nueva = obtener_version(proyecto_id, version_b)

    if anterior is None or nueva is None:
        raise ValueError(
            "Una de las versiones no existe."
        )

    campos = [
        "requisitos_funcionales",
        "requisitos_no_funcionales",
        "historias_usuario",
        "reglas_negocio",
        "criterios_aceptacion",
    ]

    diferencias = {
        "agregados": [],
        "eliminados": [],
        "modificados": [],
    }

    for campo in campos:
        elementos_a = {
            item["id"]: item
            for item in anterior["contenido"][campo]
        }

        elementos_b = {
            item["id"]: item
            for item in nueva["contenido"][campo]
        }

        for identificador, elemento in elementos_b.items():
            if identificador not in elementos_a:
                diferencias["agregados"].append({
                    "tipo": campo,
                    "elemento": elemento,
                })

            elif elementos_a[identificador] != elemento:
                diferencias["modificados"].append({
                    "tipo": campo,
                    "antes": elementos_a[identificador],
                    "despues": elemento,
                })

        for identificador, elemento in elementos_a.items():
            if identificador not in elementos_b:
                diferencias["eliminados"].append({
                    "tipo": campo,
                    "elemento": elemento,
                })

    return diferencias


def exportar_version(proyecto_id: str, version: int):
    """Exporta una versión aprobada a JSON."""

    especificacion = obtener_version(
        proyecto_id,
        version
    )

    if especificacion is None:
        raise ValueError("La versión no existe.")

    if especificacion["status"] != "APROBADA":
        raise ValueError(
            "Solo se exportan versiones aprobadas."
        )

    carpeta = BASE_DIR / "output" / proyecto_id
    carpeta.mkdir(parents=True, exist_ok=True)

    contenido = json.dumps(
        especificacion["contenido"],
        ensure_ascii=False,
        indent=2
    )

    # Archivo histórico de la versión.
    archivo = carpeta / f"architecture_v{version}.json"

    if archivo.exists():
        anterior = json.loads(
            archivo.read_text(encoding="utf-8")
        )

        if anterior != especificacion["contenido"]:
            raise RuntimeError(
                "El archivo histórico ya existe "
                "con contenido diferente."
            )
    else:
        temporal = carpeta / f"architecture_v{version}.tmp"
        temporal.write_text(contenido, encoding="utf-8")
        temporal.replace(archivo)

    # Alias de la última versión aprobada.
    actual = carpeta / "architecture.json"
    temporal_actual = carpeta / "architecture.tmp"

    temporal_actual.write_text(
        contenido,
        encoding="utf-8"
    )

    temporal_actual.replace(actual)

    return archivo



def migrar_especificaciones_previas():
    """Importa proyectos anteriores al versionado."""

    importados = 0

    with conectar() as conn:
        proyectos = conn.execute("""
            SELECT p.id, p.status
            FROM projects p
            WHERE NOT EXISTS (
                SELECT 1 FROM specifications s
                WHERE s.project_id = p.id
            )
        """).fetchall()

    for proyecto in proyectos:
        proyecto_id = proyecto["id"]
        estado = proyecto["status"]

        archivo = (
            BASE_DIR / "output" /
            proyecto_id / "architecture.json"
        )

        try:
            if estado == "APROBADO" and archivo.exists():
                data = json.loads(
                    archivo.read_text(encoding="utf-8")
                )
            else:
                with conectar() as conn:
                    mensaje = conn.execute("""
                        SELECT content
                        FROM messages
                        WHERE project_id = ?
                          AND role = 'assistant'
                        ORDER BY id DESC
                        LIMIT 1
                    """, (proyecto_id,)).fetchone()

                if mensaje is None:
                    continue

                data = json.loads(mensaje["content"])

            # Solo migrar especificaciones completas.
            if data.get("estado") != "REVISAR":
                continue

            validar_especificacion(data)

            estado_version = (
                "APROBADA" if estado == "APROBADO"
                else "EN_REVISION"
            )

            with conectar() as conn:
                conn.execute("BEGIN IMMEDIATE")

                existente = conn.execute("""
                    SELECT 1 FROM specifications
                    WHERE project_id = ?
                """, (proyecto_id,)).fetchone()

                if existente:
                    continue

                conn.execute("""
                    INSERT INTO specifications (
                        project_id,
                        version,
                        status,
                        content,
                        approved_at
                    )
                    VALUES (
                        ?, 1, ?, ?,
                        CASE WHEN ? = 'APROBADA'
                             THEN CURRENT_TIMESTAMP
                             ELSE NULL
                        END
                    )
                """, (
                    proyecto_id,
                    estado_version,
                    json.dumps(data, ensure_ascii=False),
                    estado_version,
                ))

            importados += 1

        except (OSError, ValueError) as error:
            print(
                f"No se pudo migrar {proyecto_id}: {error}"
            )

    return importados
