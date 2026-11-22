#comprueba si los datos recopilados por el modelo IA cumplen las reglas


import re

from jsonschema import validate

from agents.architect.schema import SCHEMA


def validar_especificacion(data: dict):
    """Valida estructura, estados y trazabilidad."""

    validate(instance=data, schema=SCHEMA)

    estado = data["estado"]
    preguntas = data["preguntas_pendientes"]

    if len(preguntas) > 3:
        raise ValueError(
            "Máximo 3 preguntas por interacción."
        )

    if estado == "ACLARAR":
        if not preguntas:
            raise ValueError(
                "ACLARAR requiere preguntas pendientes."
            )
        return data

    # Validaciones para estado REVISAR
    if preguntas:
        raise ValueError(
            "Existen preguntas pendientes."
        )

    if data["contradicciones"]:
        raise ValueError(
            "Existen contradicciones pendientes."
        )

    if data["bloqueos"]:
        raise ValueError(
            "Existen bloqueos críticos."
        )

    if not data["objetivo"].strip():
        raise ValueError(
            "El objetivo del proyecto está vacío."
        )

    if not data["requisitos_confirmados"]:
        raise ValueError(
            "Faltan requisitos confirmados."
        )

    # Comprobar identificadores
    grupos = {
        "requisitos_funcionales": "RF",
        "requisitos_no_funcionales": "RNF",
        "historias_usuario": "HU",
        "reglas_negocio": "RN",
        "criterios_aceptacion": "CA",
    }

    todos_ids = set()

    for campo, prefijo in grupos.items():
        for item in data[campo]:
            identificador = item["id"]

            if not re.fullmatch(
                rf"{prefijo}-\d{{3}}",
                identificador
            ):
                raise ValueError(
                    f"Identificador inválido: {identificador}"
                )

            if identificador in todos_ids:
                raise ValueError(
                    f"ID duplicado: {identificador}"
                )

            todos_ids.add(identificador)

    # Identificadores de requisitos existentes
    requisitos = (
        data["requisitos_funcionales"]
        + data["requisitos_no_funcionales"]
    )

    ids_requisitos = {
        requisito["id"]
        for requisito in requisitos
    }

    if not ids_requisitos:
        raise ValueError(
            "La especificación no contiene requisitos."
        )

    # Comprobar referencias de historias y reglas
    for campo in ["historias_usuario", "reglas_negocio"]:
        for item in data[campo]:
            relaciones = item["requisitos_relacionados"]

            if not relaciones:
                raise ValueError(
                    f"{item['id']} no tiene relaciones."
                )

            for referencia in relaciones:
                if referencia not in ids_requisitos:
                    raise ValueError(
                        f"{item['id']} referencia "
                        f"un requisito inexistente: {referencia}"
                    )

    # Comprobar criterios de aceptación
    requisitos_con_criterio = set()

    for criterio in data["criterios_aceptacion"]:
        referencia = criterio["requisito_id"]

        if referencia not in ids_requisitos:
            raise ValueError(
                f"{criterio['id']} referencia "
                f"un requisito inexistente: {referencia}"
            )

        requisitos_con_criterio.add(referencia)

    sin_criterio = (
        ids_requisitos - requisitos_con_criterio
    )

    if sin_criterio:
        raise ValueError(
            "Requisitos sin criterios de aceptación: "
            + ", ".join(sorted(sin_criterio))
        )

    return data
