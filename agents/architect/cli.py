
        if resultado["estado"] != "REVISAR":
            print("El Arquitecto devolvió un estado desconocido.")
            return

        # No aprueba si la propuesta no tiene versión activa equivalente.
        version = obtener_ultima_version(proyecto_id)
        if (
            version is None
            or version["status"] != "EN_REVISION"
            or version["contenido"] != resultado
        ):
            print("\nLa propuesta no coincide con una versión pendiente en SQLite.")
            print("Comprueba la migración y los registros de specifications.")
            return

        print(f"\nVersión v{version['version']} - EN_REVISION")
        mostrar_especificacion(resultado)
        respuesta = input(
            "\n¿Apruebas esta arquitectura? (si / cambios / salir):\n> "
        ).strip()

        if respuesta.lower() in ("si", "sí"):
            aprobar_version(proyecto_id, version["version"])
            print(f"\nVersión v{version['version']} aprobada.")
            try:
                archivo = exportar_version(proyecto_id, version["version"])
                print(f"Archivo generado: {archivo}")
            except (OSError, RuntimeError, ValueError) as error:
                print("La aprobación quedó guardada en SQLite, pero falló la exportación.")
                print(f"Detalle: {error}")
            return

        if respuesta.lower() == "salir" or not respuesta:
            print("Propuesta guardada para revisión posterior.")
            return

        if respuesta.lower() in ("cambios", "no"):
            respuesta = input("\n¿Qué cambios necesitas?\n> ").strip()
            if not respuesta:
                print("Propuesta guardada sin cambios adicionales.")
                return

        mensaje = "No apruebo esta versión. Solicito los siguientes cambios: " + respuesta
        guardar_mensaje(proyecto_id, "user", mensaje)
        historial.append({"role": "user", "content": mensaje})

    print("\nSe alcanzó el límite de interacciones de esta sesión.")
    print("Puedes continuar el proyecto después.")


def iniciar_nuevo_proyecto() -> None:
    """Crea un proyecto y comienza la conversación con el Arquitecto."""
    nombre = input("\nNombre del proyecto:\n> ").strip()
    if not nombre:
        print("Debes ingresar un nombre.")
        return

    idea = input("\nDescribe el software que deseas desarrollar:\n> ").strip()
    if not idea:
        print("Debes describir el proyecto.")
        return

    try:
        proyecto_id = crear_proyecto(nombre)
    except ValueError as error:
        print(f"No se pudo crear el proyecto: {error}")
        return

    guardar_mensaje(proyecto_id, "user", idea)
    print(f"\nProyecto creado: {nombre}")
    print(f"ID: {proyecto_id}")
    continuar_proyecto(proyecto_id)


def seleccionar_proyecto() -> None:
    """Permite elegir y continuar un proyecto existente."""
    proyectos = listar_proyectos()
    if not proyectos:
        print("\nNo hay proyectos registrados.")
        return

    print("\n===== PROYECTOS =====\n")
    for numero, proyecto in enumerate(proyectos, start=1):
        print(f"{numero}. {proyecto['name']} [{proyecto['status']}]")

    seleccion = input("\nNúmero de proyecto (o salir):\n> ").strip()
    if seleccion.lower() == "salir":
        return
    if not seleccion.isdigit():
        print("Debes ingresar un número válido.")
        return

    indice = int(seleccion) - 1
    if not 0 <= indice < len(proyectos):
        print("El proyecto seleccionado no existe.")
        return

    continuar_proyecto(proyectos[indice]["id"])


def main() -> None:
    """Punto de entrada del menú de la aplicación."""
    inicializar_database()
    migrados = migrar_especificaciones_previas()
    if migrados:
        print(f"Se migraron {migrados} especificaciones anteriores.")

    while True:
        print("\n===== AI SOFTWARE FACTORY =====")
        print("1. Crear proyecto")
        print("2. Continuar proyecto")
        print("3. Gestión documental RAG")
        print("4. Salir")
        opcion = input("\n> ").strip()

        if opcion == "1":
            iniciar_nuevo_proyecto()
        elif opcion == "2":
            seleccionar_proyecto()
        elif opcion == "3":
            menu_rag()
        elif opcion == "4":
            print("Cerrando AI Software Factory.")
            break
        else:
            print("Opción inválida.")
