"""Agent block: **output**.

Parses the raw text the model returns into a structured, cleaned result the rest
of the app can trust. Keeping this separate means prompt/model changes never leak
half-formatted strings into the API response.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplyAgentOutput:
    """Structured result of a reply generation."""

    draft: str
    context_used: int


def _clean(raw: str) -> str:
    """Strip artifacts the model sometimes adds around the reply body."""
    text = raw.strip()

    # Remove a fenced code block wrapper if the model wrapped the whole reply.
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            # drop the opening fence (possibly ```text) and the closing fence
            text = "\n".join(lines[1:-1]).strip()

    # Remove a single pair of wrapping quotes.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()

    return text


def parse_output(raw_text: str, context_used: int) -> ReplyAgentOutput:
    """Turn the model's raw completion into a :class:`ReplyAgentOutput`."""
    return ReplyAgentOutput(draft=_clean(raw_text), context_used=context_used)


if __name__ == "__main__":
    samples = [
        "  Hi Jane,\n\nThanks for the update!\n\nBest,\nJohn  ",
        '```\nHello there!\n```',
        '"Just a quick note."',
    ]
    for s in samples:
        out = parse_output(s, context_used=3)
        print(f"raw={s!r}\n -> draft={out.draft!r} context_used={out.context_used}")
    print("Output module OK")
