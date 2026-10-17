"""Provider-chain wiring for app.core.llm (no network)."""

import pytest

from app.core import llm as svc


def _settings(monkeypatch, **overrides):
    s = svc.settings.model_copy(update=overrides)
    monkeypatch.setattr(svc, "settings", s)
    return s


def test_local_primary_with_no_cloud_keys(monkeypatch):
    _settings(monkeypatch, llm_provider="local", local_llm_model="llama3.1:8b",
              groq_api_key="", openrouter_api_key="")
    chain = svc.provider_chain()
    assert [(n, m) for n, _, m in chain] == [("local", "llama3.1:8b")]
    assert chain[0][1] is svc.local_client


def test_local_primary_falls_back_to_cloud_when_keys_set(monkeypatch):
    _settings(monkeypatch, llm_provider="local", local_llm_model="qwen2.5:7b",
              groq_api_key="gsk", openrouter_api_key="sk-or")
    names = [n for n, _, _ in svc.provider_chain()]
    assert names == ["local", "groq", "openrouter"]
    # Fallbacks never receive the local model name.
    models = {n: m for n, _, m in svc.provider_chain()}
    assert models["groq"] == svc.GROQ_DEFAULT_MODEL
    assert models["openrouter"] == svc.OPENROUTER_DEFAULT_MODEL


def test_groq_primary(monkeypatch):
    _settings(monkeypatch, llm_provider="groq", groq_api_key="gsk", openrouter_api_key="")
    chain = svc.provider_chain("some-groq-model")
    assert [(n, m) for n, _, m in chain] == [("groq", "some-groq-model")]


def test_summary_chain_uses_cheap_models(monkeypatch):
    _settings(monkeypatch, llm_provider="local", local_llm_model="llama3.1:8b",
              local_llm_summary_model="", groq_api_key="gsk", openrouter_api_key="")
    models = {n: m for n, _, m in svc.provider_chain(summary=True)}
    assert models == {"local": "llama3.1:8b", "groq": svc.GROQ_SUMMARY_MODEL}


@pytest.mark.asyncio
async def test_complete_falls_through_to_next_provider():
    class Boom:
        class chat:
            class completions:
                @staticmethod
                async def create(**_):
                    raise ConnectionError("down")

    class Ok:
        class chat:
            class completions:
                @staticmethod
                async def create(**_):
                    class R:
                        choices = [type("C", (), {"message": type("M", (), {"content": "hi"})()})()]
                    return R()

    out = await svc._complete([("a", Boom(), "m1"), ("b", Ok(), "m2")], [],
                              temperature=0.1, max_tokens=5)
    assert out == "hi"


@pytest.mark.asyncio
async def test_complete_raises_when_all_fail():
    class Boom:
        class chat:
            class completions:
                @staticmethod
                async def create(**_):
                    raise ConnectionError("down")

    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        await svc._complete([("a", Boom(), "m1")], [], temperature=0.1, max_tokens=5)
