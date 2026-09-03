# ✦ CVECK Wiki

Welcome to the technical documentation for **CVECK**, an open-source, agentic system designed to adapt software engineering resumes to match target job descriptions with mathematical ATS keyword alignment, strict factual grounding, compiler auto-repair, and continuous skill-gap tracking.

```
                ┌─────────────────────────┐
                │  Job Description (JD)   │
                └────────────┬────────────┘
                             │
                             ▼
                 [ LangGraph Cyclic Engine ]
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
 [ Vector PDF + Plaintext ]       [ Market Gap Backlog ]
    output/cv-{slug}.pdf              doc/GAPS.md
```

---

## 🧭 Documentation Map

| Area | Primary Question Answered | Target Audience |
| :--- | :--- | :--- |
| **[[Getting Started]]** | *How do I run CVECK locally in under 2 minutes?* | Developers, Job Seekers |
| **[[Architecture]]** | *What are the core design invariants and system boundaries?* | Contributors, Architects |
| **[[Pipeline]]** | *What does each node in the deterministic state machine do?* | Developers, Machine Learning Engineers |
| **[[LangGraph]]** | *How is state, cyclic reflection, and routing orchestrated?* | Graph Engineers, LLM Practitioners |
| **[[ATS]]** | *How does the deterministic scoring and anti-stuffing engine work?* | Recruiters, Engineers |
| **[[Configuration]]** | *How do I manage providers (Ollama, NIM, OpenAI) and `.env`?* | Users, System Administrators |
| **[[Development]]** | *How do I compile translations, add templates, and test code?* | Contributors |
| **[[Troubleshooting]]** | *How do I diagnose 401s, compilation failures, and parser errors?* | All |

---

## ⚡ Key Architectural Invariants

1. **Physical Factual Barrier:** Output generation is strictly bounded to `doc/USER_PROFILE.md`. The LLM cannot invent unacquired skills or fake metrics.
2. **Zero-Token Local Compiles:** Typesetting is executed locally using **Typst** (`typst` Python bindings) and layout text is extracted via `pymupdf` with 0 token overhead.
3. **Deterministic Scoring:** Keyword evaluation is performed via exact regex word boundaries and strict density checks (<2%), avoiding probabilistic LLM scoring.
4. **Autonomous Gap Persistence:** Missing candidate competencies are automatically written into structured tracking backlogs (`doc/GAPS.md` and `doc/gaps.json`).