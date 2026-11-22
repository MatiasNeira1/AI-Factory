
import json
import os

from groq import Groq

from shared.config import MODEL


def generar_respuesta_json(
    historial: list,
    system_prompt: str,
    schema: dict
):
    """
    Consulta Groq y devuelve la respuesta
    convertida a un diccionario Python.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "No se encontró GROQ_API_KEY en .env"
        )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            *historial,
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "architecture_spec",
                "strict": True,
                "schema": schema,
            },
        },
        temperature=0.2,
        max_completion_tokens=3500,
    )

    # Mostrar consumo de tokens
    usage = response.usage

    if usage is not None:
        print("\n===== CONSUMO GROQ =====")
        print(f"Modelo: {MODEL}")
        print(f"Tokens de entrada: {usage.prompt_tokens}")
        print(f"Tokens de salida: {usage.completion_tokens}")
        print(f"Tokens totales: {usage.total_tokens}")
        print("=======================\n")

    # Obtener contenido de la respuesta
    content = response.choices[0].message.content

    if not content:
        raise RuntimeError(
            "Groq no devolvió una especificación."
        )

    # Convertir JSON a diccionario
    return json.loads(content)
