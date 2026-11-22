#Este archivo leerá los documentos, extraerá su texto, lo dividirá en fragmentos y guardará esos fragmentos en SQLite.
import hashlib
import re
from pathlib import Path
from uuid import uuid4

from shared.storage.database import conectar


EXTENSIONES = {".txt", ".md", ".pdf", ".docx", ".pptx"}
TAMANO_MAXIMO = 20 * 1024 * 1024


def extraer_secciones(ruta: Path) -> list[tuple[str, str]]:
    """Extrae texto conservando una ubicación de referencia."""

    extension = ruta.suffix.lower()
    secciones = []

    if extension in (".txt", ".md"):
        texto = ruta.read_text(encoding="utf-8-sig")
        secciones.append(("documento", texto))

    elif extension == ".pdf":
        from pypdf import PdfReader

        lector = PdfReader(str(ruta))

        if len(lector.pages) > 300:
            raise ValueError("El PDF supera las 300 páginas.")

        for numero, pagina in enumerate(lector.pages, 1):
            secciones.append((
                f"página {numero}",
                pagina.extract_text() or "",
            ))

    elif extension == ".docx":
        from docx import Document

        documento = Document(str(ruta))

        partes = [
            parrafo.text
            for parrafo in documento.paragraphs
            if parrafo.text.strip()
        ]

        for tabla in documento.tables:
            for fila in tabla.rows:
                partes.append(
                    " | ".join(
                        celda.text for celda in fila.cells
                    )
                )

        secciones.append((
            "contenido del documento",
            "\n".join(partes),
        ))

    elif extension == ".pptx":
        from pptx import Presentation

        presentacion = Presentation(str(ruta))

        for numero, diapositiva in enumerate(
            presentacion.slides, 1
        ):
            partes = []

            for figura in diapositiva.shapes:
                if figura.has_text_frame:
                    partes.append(figura.text)

                if figura.has_table:
                    for fila in figura.table.rows:
                        partes.append(
                            " | ".join(
                                celda.text for celda in fila.cells
                            )
                        )

            secciones.append((
                f"diapositiva {numero}",
                "\n".join(partes),
            ))

    else:
        raise ValueError(
            f"Formato no soportado: {extension}"
        )

    return secciones


def dividir_texto(
    texto: str,
    tamano: int = 1200,
    solapamiento: int = 180,
) -> list[str]:
    """Divide un texto largo en fragmentos pequeños."""

    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()

    fragmentos = []
    inicio = 0

    while inicio < len(texto):
        fin = min(inicio + tamano, len(texto))

        if fin < len(texto):
            espacio = texto.rfind(
                " ",
                inicio + int(tamano * 0.7),
                fin,
            )

            if espacio != -1:
                fin = espacio

        fragmento = texto[inicio:fin].strip()

        if fragmento:
            fragmentos.append(fragmento)

        if fin >= len(texto):
            break

        inicio = max(inicio + 1, fin - solapamiento)

    return fragmentos


def importar_documento(ruta_archivo: str) -> dict:
    """Indexa un documento sin duplicarlo."""

    ruta = Path(ruta_archivo).expanduser().resolve()

    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe el archivo: {ruta}"
        )

    if ruta.suffix.lower() not in EXTENSIONES:
        raise ValueError("Formato de archivo no soportado.")

    if ruta.stat().st_size > TAMANO_MAXIMO:
        raise ValueError(
            "El archivo supera el límite de 20 MB."
        )

    digest = hashlib.sha256(ruta.read_bytes()).hexdigest()

    with conectar() as conn:
        existente = conn.execute("""
            SELECT id FROM pm_documents
            WHERE sha256 = ?
        """, (digest,)).fetchone()

    if existente:
        return {
            "nombre": ruta.name,
            "fragmentos": 0,
            "importado": False,
        }

    fragmentos = []

    for ubicacion, texto in extraer_secciones(ruta):
        for numero, parte in enumerate(dividir_texto(texto), 1):
            fragmentos.append((
                f"{ubicacion}, fragmento {numero}",
                parte,
            ))

    if not fragmentos:
        raise ValueError(
            "No se pudo extraer texto del documento."
        )

    documento_id = str(uuid4())

    with conectar() as conn:
        conn.execute("BEGIN IMMEDIATE")

        conn.execute("""
            INSERT INTO pm_documents (id, name, sha256)
            VALUES (?, ?, ?)
        """, (documento_id, ruta.name, digest))

        for ubicacion, contenido in fragmentos:
            cursor = conn.execute("""
                INSERT INTO pm_chunks (
                    document_id, location, content
                )
                VALUES (?, ?, ?)
            """, (
                documento_id,
                ubicacion,
                contenido,
            ))

            # El rowid del índice coincide con el
            # identificador del fragmento original.
            conn.execute("""
                INSERT INTO pm_chunks_fts (rowid, content)
                VALUES (?, ?)
            """, (cursor.lastrowid, contenido))

    return {
        "nombre": ruta.name,
        "fragmentos": len(fragmentos),
        "importado": True,
    }
