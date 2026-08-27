#import "template.typ": columns-2, CV

#show: CV.with(
  name: "[NOME DO CANDIDATO]",
  lang: "pt",
  contacts: (
    ("mailto:email@exemplo.com", "email@exemplo.com"),
    ("tel:+5511999999999", "+55 (11) 99999-9999"),
    ("https://portfolio.dev", "Portfólio"),
    ("https://github.com/usuario", "GitHub"),
    ("https://linkedin.com/in/usuario", "LinkedIn")
  )
)

== RESUMO

[placeholder]

== EDUCAÇÃO

*[NOME DA INSTITUIÇÃO / UNIVERSIDADE]*
#columns-2[
  === [Bacharelado em Ciência da Computação / Curso]
  - [Mês Ano Início] – [Mês Ano Fim]
]

Disciplinas Relevantes: [placeholder]

== EXPERIÊNCIA PROFISSIONAL

#columns-2[
  === [Empresa 1]\ [Cargo / Posição]
  - [Mês Ano Início] – [Mês Ano Fim]
]

- [placeholder]
- [placeholder]
- [placeholder]

#columns-2[
  === [Empresa 2]\ [Cargo / Posição]
  - [Mês Ano Início] – [Mês Ano Fim]
]

- [placeholder]
- [placeholder]
- [placeholder]

== PROJETOS PESSOAIS (DESTAQUES)

=== #link("https://github.com/exemplo/projeto-1")[PROJETO 1]

- [placeholder]
- [placeholder]

=== #link("https://github.com/exemplo/projeto-2")[PROJETO 2]

- [placeholder]
- [placeholder]

== LICENÇAS/CERTIFICAÇÕES

- [placeholder]
- [placeholder]

== HABILIDADES E COMPETÊNCIAS

=== Front-End & Mobile
- [placeholder]

=== Backend, Dados & Arquitetura
- [placeholder]

=== Fundamentos de Engenharia & Ferramentas
- [placeholder]

=== Idiomas
- [placeholder]