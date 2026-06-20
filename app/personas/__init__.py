from app.personas import booking_assistant as _ba
from app.personas import sales_agent as _sa
from app.personas._base import Persona
from app.personas._shared import compose_system_prompt

PERSONAS: dict[str, Persona] = {
    _ba.persona.key: _ba.persona,
    _sa.persona.key: _sa.persona,
}


def get_persona(key: str) -> Persona:
    if key not in PERSONAS:
        raise KeyError(f"unknown persona key: {key!r}")
    return PERSONAS[key]


def system_prompt_for(key: str, **context: str) -> str:
    body = get_persona(key).body_prompt
    if context:
        body = body.format(**context)
    return compose_system_prompt(body)


__all__ = ["PERSONAS", "Persona", "get_persona", "system_prompt_for"]
