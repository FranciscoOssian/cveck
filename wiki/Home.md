# ✦ CVECK Wiki

Welcome to the technical documentation for **CVECK**, an open-source, agentic system designed to adapt software engineering resumes to match target job descriptions with mathematical ATS keyword alignment, strict factual grounding, compiler auto-repair, continuous skill-gap tracking, and native Model Context Protocol (MCP) support.

```
                ┌─────────────────────────┐
                │  Job Description (JD)   │
                └────────────┬────────────┘
                             │
                             ▼
         [ Core Engine & Declarative Workflow ]
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
 [ LangGraph Cyclic Adapter ]     [ MCP Server Adapter ]
   (Interactive Rich CLI)          (IDE / Agent Tools)
             │                               │
             └───────────────┬───────────────┘
                             ▼
 ┌───────────────────────────────────────────────────────────┐
 │                     Output Artifacts                      │
 ├───────────────────────────────────────────────────────────┤
 │ • Vector PDF + TXT Layout (output/cv-{slug}.pdf)          │
 │ • Audited Pruned Profile (output/profile_pruned-{slug}.md)│
 │ • Market Gap Backlog (doc/GAPS.md & doc/gaps.json)        │
 │ • Extracted ATS Keywords (output/job_terms-{slug}.json)   │
 └───────────────────────────────────────────────────────────┘
```

---

## 🧭 Documentation Map

| Area | Primary Question Answered | Target Audience |
| :--- | :--- | :--- |
| **[[Getting Started]]** | *How do I run CVECK CLI or start the MCP server?* | Developers, Job Seekers |
| **[[Architecture]]** | *What is the Core & Adapter Pattern design?* | Contributors, Architects |
| **[[Pipeline]]** | *What does each step in the declarative pipeline do?* | Developers, ML Engineers |
| **[[LangGraph]]** | *How is the graph dynamically compiled from `workflow.yaml`?* | Graph Engineers, LLM Practitioners |
| **[[ATS]]** | *How does the deterministic scoring and anti-stuffing engine work?* | Recruiters, Engineers |
| **[[Configuration]]** | *How do I manage providers, `workflow.yaml` policies, and `.env`?* | Users, System Administrators |
| **[[Development]]** | *How do I add use cases, templates, and compile translations?* | Contributors |
| **[[Troubleshooting]]** | *How do I diagnose 401s, compilation failures, and MCP errors?* | All |

---

## ⚡ Key Architectural Invariants

1. **Physical Factual Barrier:** Output generation is strictly bounded to `doc/USER_PROFILE.md`. The LLM cannot invent unacquired skills or fake metrics.
2. **Core Domain Separation (Adapter Pattern):** Pure business logic, models, and use cases reside in `src/core/`, completely decoupled from orchestration frameworks (LangGraph, MCP).
3. **Declarative Workflow (`workflow.yaml`):** Pipeline policies (scoring thresholds, retry limits, bullet budgets) and transition rules are defined declaratively in YAML and validated via Pydantic schemas.
4. **Decoupled Profile Pruning:** A dedicated cognitive step (`profile_pruner`) filters technical noise and orphan complexity before typesetting; `cv_generator` and `cv_refiner` consume strictly the pruned profile.
5. **Dual Interface:** Run interactively via the Rich CLI (`cveck`) or integrate directly with AI IDEs / agents via Model Context Protocol (`cveck mcp`).
6. **Zero-Token Local Compiles:** Typesetting is executed locally using **Typst** (`typst` Python bindings) and layout text is extracted via `pymupdf` with 0 token overhead.
7. **Deterministic Scoring:** Keyword evaluation is performed via exact regex word boundaries and strict density checks (<2%), avoiding probabilistic LLM scoring.
8. **Autonomous Gap Persistence:** Missing candidate competencies are automatically written into structured tracking backlogs (`doc/GAPS.md` and `doc/gaps.json`).

---

## Proposta de Corpo do Pull Request (PR)

Abaixo está o texto completo pronto para ser utilizado na abertura do Pull Request:

```markdown
# refactor: introduce adapter pattern, declarative workflow.yaml, and MCP server

## 📌 Overview

This PR refactors the CVECK codebase to decouple pure domain logic from execution frameworks using the **Adapter Pattern**. 

Business rules, services, models, and use cases now live cleanly in `src/core/`, while orchestration engines and interfaces (`LangGraph`, `MCP Server`, and `Rich CLI`) act as dedicated adapters. Additionally, pipeline policies and transitions are now declared in `src/core/workflow.yaml`.