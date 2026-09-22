#let contact_header(links) = {
  set align(center)
  grid(
    columns: links.len(),
    gutter: 3%,
    ..links.map(v => box(link(v.at(0))[#v.at(1)]))
  )
}

#let CV(
  name: "YOUR FULL NAME",
  contacts: (),
  lang: "pt",
  body
) = {
  set text(lang: lang)
  set page(margin: 1.5cm)
  
  show link: underline
  show heading.where(level: 1): set align(center)
  show heading.where(level: 2): set align(center)
  set par(
    justify: true
  )

  [= #upper(name)]

  align(center)[
    #line(length: 78%)
  ]

  if contacts.len() > 0 {
    contact_header(contacts)
  }

  body
}

#let columns-2 = (body, gutter: 40%) => {
  let clened = body.fields().children.filter(value => value != [ ])
  set list(marker: [])
  columns(2, gutter: gutter)[
    #align(left)[#clened.at(0)]
    #colbreak()
    #align(right)[#clened.at(1)]
  ]
}