from src.core.context import load_user_profile, resolve_template_skeleton
from src.core.paths import DOC_DIR, PROMPTS_DIR, TEMPLATES_DIR


def get_workflow_instructions(job_description: str, lang: str = "pt") -> str:
    """Generates the complete workflow instructions, injecting user profile, style guide, and Typst skeleton."""
    user_profile = load_user_profile(DOC_DIR)
    style_guide = (PROMPTS_DIR / "CV_STYLE_GUIDE.md").read_text(encoding="utf-8")
    template_skeleton, _ = resolve_template_skeleton(TEMPLATES_DIR, lang)

    return f"""✦ CVECK — ADAPTADOR AUTÔNOMO DE CURRÍCULOS

SUA MISSÃO:
Adaptar o currículo do candidato para a vaga fornecida, atingindo nota máxima no ATS com fidelidade factual absoluta e formatação Typst profissional.

---
BARREIRA FACTUAL INEGOCIÁVEL:
1. Use EXCLUSIVAMENTE informações presentes no PERFIL FACTUAL.
2. É ESTRITAMENTE PROIBIDO inventar tecnologias, empresas, métricas ou certificados.
3. Se a vaga exigir competências que o candidato não possui, registre-as usando `record_gaps`. NUNCA as inclua no currículo.

---
REGRAS OBRIGATÓRIAS DE FORMATAÇÃO TYPST:
1. Você DEVE obrigatoriamente preencher o bloco `#show: CV.with(...)` com o nome e contatos do candidato conforme o ESQUELETO BASE abaixo.
2. NUNCA crie cabeçalhos manuais com `#align(center)` ou `#set page/text` soltos.
3. Toda empresa e cargo DEVE usar o bloco `#columns-2` para garantir o alinhamento de datas à direita.
4. Títulos de seção DEVEM usar dois sinais de igual (`== RESUMO`, `== EXPERIÊNCIA PROFISSIONAL`).

---
ESQUELETO BASE TYPST OBRIGATÓRIO (Preencha os placeholders a partir dele):
```typst
{template_skeleton}
```

---
GUIA DE ESTILO (CV_STYLE_GUIDE.md):
{style_guide}

---
PERFIL FACTUAL DO CANDIDATO (USER_PROFILE.md):
{user_profile}

---
VAGA ALVO:
{job_description}
"""