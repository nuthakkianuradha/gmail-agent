from pydantic import BaseModel


class PersonaRequest(BaseModel):
    display_name: str = ""
    tone: str = "professional"
    style_notes: str = ""
    signature: str = ""
    language: str = "en"
    custom_instructions: str = ""


class PersonaResponse(BaseModel):
    id: str
    display_name: str | None = None
    tone: str = "professional"
    style_notes: str | None = None
    signature: str | None = None
    language: str = "en"
    custom_instructions: str | None = None


class RuleRequest(BaseModel):
    rule_text: str
    category: str = "general"


class RuleResponse(BaseModel):
    id: str
    rule_text: str
    category: str
    is_active: bool
    priority: int


if __name__ == "__main__":
    p = PersonaRequest(display_name="John", tone="casual", signature="Cheers, John")
    print(f"PersonaRequest: {p.model_dump_json(indent=2)}")

    r = RuleRequest(rule_text="Always be formal", category="tone")
    print(f"RuleRequest: {r.model_dump_json()}")
    print("Persona models OK")
