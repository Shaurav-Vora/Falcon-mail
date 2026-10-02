# Falcon Mail Corpus v2 sources

## Falcon Mail v1

- File: `data/raw/falcon_mail_v1/complaints.csv`
- Records: 585
- Type: synthetic campus-ticket examples created for this project
- Labels: Falcon Mail's 11 categories and 4 urgency levels
- Grouping: `template_group_id` keeps paraphrases/templates in one split

The raw file is a byte-for-byte snapshot of `data/complaints.csv` taken before Corpus v2
preparation.

## University Students Complaints Dataset

- Files: `data/raw/university_students_complaints/train.csv` and `test.csv`
- Records: 332
- Type: external; described by the publisher as student complaints
- Publisher: Md. Al Amin
- Revision: `3a21d7a28cca2dad1ced731246772810798215f7`
- Source: <https://huggingface.co/datasets/alaminxpro/university-students-complaints>
- License: CC BY 4.0
- Citation: `Al Amin, Md. (2026). University Students Complaints Dataset. Hugging Face.`

The source has five broad category labels and four severity labels. These do not align
directly with Falcon Mail. Corpus preparation therefore preserves the original labels and
applies the documented adjudication rules in `label_mapping.json`. Publisher `Urgent` is
mapped to Falcon Mail `High`; only explicit safety-emergency language is elevated to
`Critical`. Broad Infrastructure records are separated using their primary department
and complaint text. Publisher aspect tags are retained for audit but are not trusted as
direct Falcon Mail labels because many rows carry unrelated secondary aspects.

## Audit notes

- External rows: 332
- External paraphrase groups: 186
- Exact duplicate external texts after case/whitespace normalization: 5
- Publisher groups containing more than one severity: 1
- Personal/context fields excluded from model features: Gender, Semester, Student_Dept,
  and Timestamp
- Split rule: deterministic 70/15/15 assignment by incident/template group using seed 42

The external source expands domain language but remains small and publisher-labelled.
Evaluation must therefore report external and synthetic records separately.
