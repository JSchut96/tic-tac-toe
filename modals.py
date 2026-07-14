from dataclasses import dataclass, field

@dataclass
class Message:
    type: str
    payload: dict = field(default_factory=dict)
