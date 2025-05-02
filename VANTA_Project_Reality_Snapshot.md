# 📦 **VANTA Project - Symbolic Swarm Online v1 (External AI Intelligence Package)**

---

## 1️⃣ PROJECT OVERVIEW

**VANTA** is a modular agentic framework designed for **symbolic identity-driven task execution**, managed by a central orchestrator ("Crown") and populated with agent instances called **Pilgrims**.

Each agent:
- Has a symbolic narrative role.
- Can execute tasks.
- Can communicate with other Pilgrims via A2A messaging.
- Can process or request external tool functions (MCP tooling layer - optional for now).

VANTA is designed to eventually support swarm intelligence, stigmergic communication, and mythic narrative encoding into tasks.

---

## 2️⃣ KEY CONCEPTS & TERMINOLOGY

| Term                      | Description                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------- |
| VantaMasterCore ("Crown") | Central orchestrator → loads agents, routes tasks, manages swarm logic.            |
| Pilgrims                  | Individual agents (loaded from `blueprint.yaml`) → each has symbolic identity + task logic. |
| blueprint.yaml            | Declarative config → lists active Pilgrims, their roles, settings, and startup positions. |
| Symbolic Identity         | Each Pilgrim has `archetype` + `mythos_role` → used for narrative and ritual awareness. |
| A2A (Agent to Agent)      | Pilgrims can send tasks/messages to each other using `PilgrimCommunicatorMixin`.   |
| MCP Tooling               | Pilgrims (ToolAgent) can process tool requests → scaffolded but basic live version exists. |

---

## 3️⃣ DIRECTORY STRUCTURE (Simplified)

```
/
├── vanta_seed/
│   ├── core/
│   │   └── vanta_master_core.py
│   ├── agents/
│   │   ├── echo_agent.py
│   │   ├── memory_agent.py
│   │   ├── symbolic_agent.py
│   │   ├── tool_agent.py
│   │   └── agent_utils.py
├── blueprint.yaml             # (At root, not in config/ currently)
├── run.py
├── theplan.md
├── requirements.txt
├── config.py                  # (Handles env loading, logging etc.)
└── ... (other project files)
```

---

## 4️⃣ KEY FILES

| File                       | Role                                                              |
| -------------------------- | ----------------------------------------------------------------- |
| `run.py`                     | FastAPI Server → starts VantaMasterCore + API endpoints           |
| `vanta_master_core.py`     | Core orchestrator logic → loads blueprint, handles tasks + routing |
| `blueprint.yaml`           | Declarative agent list + settings + symbolic identity           |
| `agent_utils.py`           | Shared mixins → A2A (PilgrimCommunicatorMixin), MCP (MCPToolingMixin) |
| `agents/*.py`              | Real Pilgrim implementations (Echo, Memory, Symbolic, Tool)       |
| `config.py`                | Env loading, logging, path management                           |
| `theplan.md`               | Project narrative and conceptual vision                           |

---

## 5️⃣ BLUEPRINT AGENT EXAMPLE

```yaml
- name: SymbolicAgent
  class: vanta_seed.agents.symbolic_agent.SymbolicAgent
  symbolic_identity:
    archetype: "Compressor"
    mythos_role: "Weaver of Collapse"
  settings:
    compression_level: 0.8
  initial_trinity_state:
    position: [0.0, 1.0, 0.0]
```

---

## 6️⃣ EXECUTION FLOW (Task Routing)

```
Client POST -> run.py (FastAPI endpoint)
→ VantaMasterCore.submit_task
→ _route_task (choose agent)
→ _run_task_on_pilgrim
→ Pilgrim.execute (logic runs)
→ Crown updates state / trails (optional)
→ Response sent back to client
```

---

## 7️⃣ API OVERVIEW

| Endpoint                    | Description                              |
| --------------------------- | ---------------------------------------- |
| `GET /`                       | Basic status                             |
| `POST /submit_task`           | Generic task execution (via `TaskRequest`) |
| `POST /v1/chat/completions` | OpenAI style chat endpoint (optional)   |

→ API Key (`Authorization: Bearer <key>`) required but permissive at this stage.

---

## 8️⃣ CURRENT CAPABILITIES + LIMITATIONS

✅ **Symbolic Swarm Online v1 milestone achieved**
- All Pilgrims defined → loaded → running
- Agents self-announce + describe identity on request
- A2A working via PilgrimCommunicatorMixin
- ToolAgent now live handles `ToolCall` (`query` and `calculate`)
- Swarm stigmergic storage present (simple version)

🟡 **Ritualization + Advanced Swarm next**
- Purpose Pulse + dynamic role changes → NOT YET
- Complex stigmergic routing → basic only
- MCP ToolAgent → only basic tool processing, no external tool API yet
- PluginManager → minimal loading

---

## ✅ STATUS SUMMARY (What is done + where we are)

| Status | Layer                                                                 |
| ------ | --------------------------------------------------------------------- |
| ✅     | Core orchestration (VantaMasterCore + API)                            |
| ✅     | Agent loading + symbolic identities                                     |
| ✅     | Pilgrim self-awareness (startup announce + identity query)              |
| ✅     | Basic A2A communication                                               |
| ✅     | Basic MCP tool handling (ToolAgent live)                              |
| 🟡     | Advanced swarm logic (purpose vector routing, stigmergic radius search, role pulses) |
| 🟡     | External tool integration (beyond basic ToolCall)                       |

---

## 🧭 NEXT STEPS (Ritualization Patch v3 Proposal → optional to show AI)

> Integrate Purpose Pulse → trigger agents based on global narrative
> Extend stigmergic logic → true swarm adjacency + role awareness
> Add symbolic escalation + compression thresholds → self-mutation seeds

---

## 📌 FINAL PACKAGE SUMMARY

→ The VANTA system right now is a **modular agentic framework with a Crown + Pilgrims model**, supporting:

✅ Swarm orchestration
✅ Symbolic identity + narrative roles
✅ Agent-to-agent communication
✅ Tool handling scaffold + live toolcall capability
✅ Declarative config (`blueprint.yaml`)

→ It is at milestone `"Symbolic Swarm Online v1"` → READY for next phase of swarm evolution, ritual behaviors, and MCP integration.

--- 