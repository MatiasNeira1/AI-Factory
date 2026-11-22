
import sqlite3
from contextlib import contextmanager

from shared.config import BASE_DIR


DB_PATH = BASE_DIR / "data" / "factory.db"


@contextmanager
def conectar():
    """Abre una conexión SQLite con transacciones."""

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    # Habilitar claves foráneas
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def inicializar_database():
    """Crea las tablas del sistema si no existen."""

    with conectar() as conn:

        # ==========================================
        # 1. TABLA DE PROYECTOS
        # ==========================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL
                    DEFAULT 'EN_PROCESO'
                    CHECK (
                        status IN (
                            'EN_PROCESO',
                            'APROBADO'
                        )
                    ),
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # 2. TABLA DE CONVERSACIONES
        # ==========================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK (
                        role IN ('user', 'assistant')
                    ),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (project_id)
                    REFERENCES projects(id)
                    ON DELETE CASCADE
            )
        """)

        # 3. Índice de conversaciones
        conn.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_messages_project
            ON messages(project_id, id)
        """)

        # ==========================================
        # 4. TABLA DE VERSIONES DE ARQUITECTURA
        # ==========================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS specifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                project_id TEXT NOT NULL,

                version INTEGER NOT NULL
                    CHECK (version >= 1),

                status TEXT NOT NULL
                    DEFAULT 'EN_REVISION'
                    CHECK (
                        status IN (
                            'BORRADOR',
                            'EN_REVISION',
                            'APROBADA',
                            'SUSTITUIDA'
                        )
                    ),

                content TEXT NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                approved_at TEXT,

                FOREIGN KEY (project_id)
                    REFERENCES projects(id)
                    ON DELETE CASCADE,

                UNIQUE (project_id, version)
            )
        """)

        # 5. Índice para buscar versiones
        conn.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_specifications_project
            ON specifications(project_id, version)
        """)

        # 6. Una propuesta activa por proyecto
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                idx_specifications_in_review
            ON specifications(project_id)
            WHERE status = 'EN_REVISION'
        """)

        # ==========================================
        # 7. CONFIGURACIÓN OPCIONAL DE RAG
        # ==========================================

        # Obtener columnas existentes de projects
        columnas = {
            fila["name"]
            for fila in conn.execute(
                "PRAGMA table_info(projects)"
            )
        }

        # Agregar configuración RAG solo si
        # todavía no existe en la tabla
        if "pm_rag_enabled" not in columnas:
            conn.execute("""
                ALTER TABLE projects
                ADD COLUMN pm_rag_enabled INTEGER
                    NOT NULL DEFAULT 0
                    CHECK (pm_rag_enabled IN (0, 1))
            """)

        # ==========================================
        # 8. DOCUMENTOS DE GESTIÓN DE PROYECTOS
        # ==========================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pm_documents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sha256 TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==========================================
        # 9. FRAGMENTOS DE LOS DOCUMENTOS
        # ==========================================

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pm_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                document_id TEXT NOT NULL,

                location TEXT NOT NULL,

                content TEXT NOT NULL,

                FOREIGN KEY (document_id)
                    REFERENCES pm_documents(id)
                    ON DELETE CASCADE
            )
        """)

        # Índice para buscar fragmentos por documento
        conn.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_pm_chunks_document
            ON pm_chunks(document_id)
        """)

        # ==========================================
        # 10. ÍNDICE DE BÚSQUEDA RAG (FTS5)
        # ==========================================

        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS
                pm_chunks_fts
            USING fts5(
                content,
                tokenize='unicode61 remove_diacritics 2'
            )
        """)
