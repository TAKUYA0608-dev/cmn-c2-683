# CMN-C2-683 — Structured Output & Constrained Decoding Reliability Q&A Agent

> **Category**: Cat 2 (domain workflow (a job to be done))
> **Industry**: Common (industry-agnostic)

## Overview

Advisory question-answering about making structured LLM output reliable. Given a JSON request with a question (for example "How strict should my JSON Schema be for structured output?") and optionally the constraints already declared, the agent checks that the input is neither executable code nor confidential material, redacts credentials, classifies the concern, retrieves matching records from a versioned knowledge base by deterministic keyword scoring, and composes a reliability plan conditioned on the retrieved records, with citations and a verification checklist. The pipeline has no LLM step. It is advisory: it never decodes or repairs JSON itself, runs no tool call and changes no schema, prompt or configuration; the output is a draft with a disclaimer, unmatched questions get an explicit out-of-scope answer, claims without a supporting record are rejected, and over-long or injection-like input is discarded with a named error code. The knowledge base shipped here is a small seeded sample — replace it with your own engineering guidance.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later (`requires-python = ">=3.11"`) |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and operational documentation
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
