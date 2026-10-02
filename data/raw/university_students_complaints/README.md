# University Students Complaints Dataset

This directory contains the two CSV files used from
[`alaminxpro/university-students-complaints`](https://huggingface.co/datasets/alaminxpro/university-students-complaints).

- Revision: `3a21d7a28cca2dad1ced731246772810798215f7`
- Files: `train.csv` and `test.csv`
- Publisher: Md. Al Amin
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Publisher description: 332 English university-student complaints in 186 paraphrase groups

The files are kept unchanged. Their labels are not treated as Falcon Mail ground truth:
`training/prepare_corpus_v2.py` preserves every original label and records the reviewed
Falcon Mail label separately. Gender, semester, student department, and timestamp are
not copied into the training corpus.

Run `python training/fetch_external_corpus.py` to verify existing files or retrieve the
pinned copies. The downloader checks both headers and SHA-256 hashes before publishing a
download.
