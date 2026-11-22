
from unittest.mock import Mock

import pytest

from agents.architect import agent


def test_autocorreccion_exitosa(monkeypatch):
    """La segunda respuesta supera la validación."""

    historial = [
        {
            "role": "user",
            "content": "Crear una API de inventario",
        }
    ]

    # Simulamos dos respuestas de Groq.
    generar = Mock(side_effect=[
        {"estado": "REVISAR", "id": "RF-999"},
        {"estado": "REVISAR", "id": "RF-001"},
    ])

    # La primera validación falla.
    validar = Mock(side_effect=[
        ValueError("Identificador incorrecto"),
        {"estado": "REVISAR", "id": "RF-001"},
    ])

    monkeypatch.setattr(
        agent,
        "generar_respuesta_json",
        generar,
    )

    monkeypatch.setattr(
        agent,
        "validar_especificacion",
        validar,
    )

    resultado = agent.consultar_arquitecto(
        historial
    )

    assert resultado["id"] == "RF-001"
    assert generar.call_count == 2
    assert validar.call_count == 2

    # La función no modifica el historial original.
    assert len(historial) == 1


def test_reintentos_agotados(monkeypatch):
    """Se detiene después de tres respuestas inválidas."""

    generar = Mock(
        return_value={"estado": "REVISAR"}
    )

    validar = Mock(
        side_effect=ValueError("JSON inválido")
    )

    monkeypatch.setattr(
        agent,
        "generar_respuesta_json",
        generar,
    )

    monkeypatch.setattr(
        agent,
        "validar_especificacion",
        validar,
    )

    with pytest.raises(agent.ErrorArquitecto):
        agent.consultar_arquitecto([
            {
                "role": "user",
                "content": "Crear una aplicación",
            }
        ])

    assert generar.call_count == 3


def test_error_servicio_no_se_reintenta(monkeypatch):
    """No reintentar fallos ajenos a la validación."""

    generar = Mock(
        side_effect=RuntimeError(
            "Error del proveedor de IA"
        )
    )

    monkeypatch.setattr(
        agent,
        "generar_respuesta_json",
        generar,
    )

    with pytest.raises(RuntimeError):
        agent.consultar_arquitecto([
            {
                "role": "user",
                "content": "Crear una API",
            }
        ])

    assert generar.call_count == 1
