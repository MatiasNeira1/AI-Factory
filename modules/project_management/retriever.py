#Este módulo buscará los fragmentos que más se relacionen con la consulta del usuario.
import re

from shared.storage.database import conectar


PALABRAS_COMUNES = {
    "quiero", "necesito", "tengo", "hacer",
    "crear", "agregar", "sistema", "software",
    "aplicacion", "para", "como", "sobre",
    "este", "esta", "estos", "estas",
    "puedo", "debo", "deberia", "tambien",
    "cuando", "donde", "desde", "entre",
    "porque", "seria", "quieres",
}


def buscar_fragmentos(
    consulta: str,
    limite: int = 4,
) -> list[dict]:
    """Recupera fragmentos mediante SQLite FTS5."""

    if not 1 <= limite <= 10:
        raise ValueError("Límite de resultados inválido.")

    palabras = re.findall(
        r"[^\W\d_]{3,}",
        consulta.lower(),
        flags=re.UNICODE,
    )

    terminos = []
    vistos = set()

    for palabra in palabras:
        if palabra in PALABRAS_COMUNES:
            continue

        if palabra in vistos:
            continue

        vistos.add(palabra)

        # Búsqueda por prefijo para tolerar
        # algunas variaciones de las palabras.
        prefijo = (
            palabra[:-1] if len(palabra) > 4
            else palabra
        )

        terminos.append(prefijo + "*")

        if len(terminos) == 8:
            break

    if not terminos:
        return []

    consulta_fts = " OR ".join(terminos)

    with conectar() as conn:
        filas = conn.execute("""
            SELECT
                d.name AS documento,
                c.location AS ubicacion,
                c.content AS contenido,
                bm25(pm_chunks_fts) AS puntuacion
            FROM pm_chunks_fts
            JOIN pm_chunks c
                ON c.id = pm_chunks_fts.rowid
            JOIN pm_documents d
                ON d.id = c.document_id
            WHERE pm_chunks_fts MATCH ?
            ORDER BY puntuacion ASC
            LIMIT ?
        """, (consulta_fts, limite)).fetchall()

    return [dict(fila) for fila in filas]
