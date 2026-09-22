#import "template.typ": columns-2, CV

#show: CV.with(
  name: "[求职者姓名]",
  lang: "zh",
  contacts: (
    ("mailto:email@example.com", "email@example.com"),
    ("tel:+8613800138000", "+86 138-0013-8000"),
    ("https://portfolio.dev", "个人作品集"),
    ("https://github.com/username", "GitHub"),
    ("https://linkedin.com/in/username", "LinkedIn")
  )
)

== 个人总结

[placeholder]

== 教育背景

*[大学名称 / 教育机构]*
#columns-2[
  === [计算机科学与技术 / 本科]
  - [开始年月] – [结束年月]
]

相关课程: [placeholder]

== 工作经历

#columns-2[
  === [公司名称 1]\ [职位名称]
  - [开始年月] – [结束年月]
]

- [placeholder]
- [placeholder]
- [placeholder]

#columns-2[
  === [公司名称 2]\ [职位名称]
  - [开始年月] – [结束年月]
]

- [placeholder]
- [placeholder]
- [placeholder]

== 个人项目（重点项目）

=== #link("https://github.com/example/project-1")[项目 1]

- [placeholder]
- [placeholder]

=== #link("https://github.com/example/project-2")[项目 2]

- [placeholder]
- [placeholder]

== 资格证书

- [placeholder]
- [placeholder]

== 专业技能

=== 前端与移动端
- [placeholder]

=== 后端、数据与架构
- [placeholder]

=== 工程基础与AI工具
- [placeholder]

=== 语言能力
- [placeholder]