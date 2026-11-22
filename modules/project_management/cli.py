
from shared.storage.database import conectar
from shared.storage.project_repository import listar_proyectos

from modules.project_management.ingestion import importar_documento
from modules.project_management.retriever import buscar_fragmentos
from modules.project_management.service import configurar_rag


def elegir_proyecto():
    proyectos = listar_proyectos()

    if not proyectos:
        print("Primero debes crear un proyecto.")
        return None

    print("\nProyectos disponibles:")

    for numero, proyecto in enumerate(proyectos, 1):
        print(f"{numero}. {proyecto['name']}")

    opcion = input("\nNúmero de proyecto: ").strip()

    if not opcion.isdigit():
        print("Selección inválida.")
        return None

    indice = int(opcion) - 1

    if not 0 <= indice < len(proyectos):
        print("El proyecto no existe.")
        return None

    return proyectos[indice]["id"]


def mostrar_documentos():
    with conectar() as conn:
        documentos = conn.execute("""
            SELECT d.name, COUNT(c.id) AS fragmentos
            FROM pm_documents d
            LEFT JOIN pm_chunks c
                ON c.document_id = d.id
            GROUP BY d.id
            ORDER BY d.name
        """).fetchall()

    if not documentos:
        print("\nLa biblioteca está vacía.")
        return

    print("\nDocumentos indexados:")

    for documento in documentos:
        print(
            f"- {documento['name']} "
            f"({documento['fragmentos']} fragmentos)"
        )


def menu_rag():
    while True:
        print("\n===== GESTIÓN DOCUMENTAL RAG =====")
        print("1. Importar documento")
        print("2. Listar documentos")
        print("3. Activar RAG en un proyecto")
        print("4. Desactivar RAG en un proyecto")
        print("5. Probar búsqueda documental")
        print("6. Volver")

        opcion = input("\n> ").strip()

        if opcion == "1":
            ruta = input(
                "\nRuta completa del documento:\n> "
            ).strip().strip('"')

            try:
                resultado = importar_documento(ruta)

                if resultado["importado"]:
                    print(
                        f"\nImportado: {resultado['nombre']}"
                    )
                    print(
                        f"Fragmentos: {resultado['fragmentos']}"
                    )
                else:
                    print(
                        "\nEste documento ya está indexado."
                    )

            except Exception as error:
                print(f"No se pudo importar: {error}")

        elif opcion == "2":
            mostrar_documentos()

        elif opcion in ("3", "4"):
            proyecto_id = elegir_proyecto()

            if proyecto_id:
                activar = opcion == "3"

                configurar_rag(proyecto_id, activar)

                estado = (
                    "activado" if activar
                    else "desactivado"
                )

                print(f"\nRAG {estado} correctamente.")

        elif opcion == "5":
            consulta = input(
                "\n¿Qué deseas buscar?:\n> "
            ).strip()

            resultados = buscar_fragmentos(consulta)

            if not resultados:
                print("No se encontraron fragmentos.")
                continue

            for resultado in resultados:
                print(
                    f"\nDocumento: {resultado['documento']}"
                )
                print(
                    f"Ubicación: {resultado['ubicacion']}"
                )
                print(
                    f"Contenido:\n"
                    f"{resultado['contenido'][:450]}..."
                )

        elif opcion == "6":
            return

        else:
            print("Opción inválida.")
