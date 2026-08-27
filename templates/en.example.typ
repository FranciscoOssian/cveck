#import "template.typ": columns-2, CV

#show: CV.with(
  name: "[CANDIDATE NAME]",
  lang: "en",
  contacts: (
    ("mailto:email@example.com", "email@example.com"),
    ("tel:+1234567890", "+1 (234) 567-890"),
    ("https://portfolio.dev", "Portfolio"),
    ("https://github.com/username", "GitHub"),
    ("https://linkedin.com/in/username", "LinkedIn")
  )
)

== SUMMARY

[placeholder]

== EDUCATION

*[UNIVERSITY / INSTITUTION NAME]*
#columns-2[
  === [Bachelor of Science in Computer Science / Degree]
  - [Start Date] – [End Date]
]

Relevant Coursework: [placeholder]

== PROFESSIONAL EXPERIENCE

#columns-2[
  === [Company 1]\ [Job Title]
  - [Start Date] – [End Date]
]

- [placeholder]
- [placeholder]
- [placeholder]

#columns-2[
  === [Company 2]\ [Job Title]
  - [Start Date] – [End Date]
]

- [placeholder]
- [placeholder]
- [placeholder]

== PERSONAL PROJECTS (HIGHLIGHTS)

=== #link("https://github.com/example/project-1")[PROJECT 1]

- [placeholder]
- [placeholder]

=== #link("https://github.com/example/project-2")[PROJECT 2]

- [placeholder]
- [placeholder]

== LICENSES & CERTIFICATIONS

- [placeholder]
- [placeholder]

== SKILLS & COMPETENCIES

=== Front-End & Mobile
- [placeholder]

=== Backend, Data & Architecture
- [placeholder]

=== Engineering Fundamentals & AI
- [placeholder]

=== Languages
- [placeholder]