"""Package-boundary guard.

The backend is three teachable subsystems on top of shared plumbing:

    core  <-  mcp, rag, agent        (core imports none of them)
    mcp   <-  agent, routers         (mcp imports neither rag nor agent)
    rag   <-  agent, routers         (rag imports neither mcp nor agent)
    agent <-  routers                (agent is the only place mcp + rag + llm meet)

These tests fail the moment someone wires a shortcut across a boundary.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"


def _imports(py: Path) -> set[str]:
    tree = ast.parse(py.read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app"):
            found.add(node.module)
            # `from app.mcp import gmail` names a submodule, not just a package
            found.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("app"))
    return found


def _package_imports(pkg: str) -> dict[str, set[str]]:
    return {str(p.relative_to(APP)): _imports(p) for p in (APP / pkg).rglob("*.py")}


def _violations(pkg: str, forbidden_prefixes: tuple[str, ...]) -> list[str]:
    out = []
    for file, mods in _package_imports(pkg).items():
        for m in mods:
            if m.startswith(forbidden_prefixes):
                out.append(f"{file} imports {m}")
    return out


def test_core_imports_no_subsystem():
    assert _violations("core", ("app.mcp", "app.rag", "app.agent", "app.routers")) == []


def test_mcp_is_independent_of_rag_and_agent():
    assert _violations("mcp", ("app.rag", "app.agent", "app.core", "app.routers")) == []


def test_rag_is_independent_of_mcp_and_agent():
    assert _violations("rag", ("app.mcp", "app.agent", "app.routers")) == []


def test_agent_never_imports_routers():
    assert _violations("agent", ("app.routers",)) == []


def test_gmail_sdk_wrapper_is_used_only_by_mcp_server():
    """All Gmail access goes through MCP tools: only server.py may touch the SDK."""
    users = [
        str(p.relative_to(APP))
        for p in APP.rglob("*.py")
        if "app.mcp.gmail" in _imports(p) and p.name != "gmail.py"
    ]
    assert users == ["mcp/server.py"], users


def test_no_legacy_packages():
    for legacy in ("services", "utils", "db"):
        assert not (APP / legacy).exists(), f"app/{legacy} should be gone"
