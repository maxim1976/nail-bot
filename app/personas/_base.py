from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    key: str
    display_name: str
    welcome_message: str
    quick_replies: tuple[str, ...]
    body_prompt: str
