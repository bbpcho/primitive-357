# The Primitive Generalized Fermat Equation x³+y⁵=z⁷

**A computer-assisted proof — Peter Chocian, Independent researcher**

This repository holds the paper proving that `x^3 + y^5 = z^7` has no solution in nonzero coprime integers, its LaTeX source, and the computational companion that makes every project-specific finite calculation replayable. The full audit history of how the proof was reached — snapshots, withdrawn archives and the replacement release of 15 September 2026 — remains in [`bbpcho/primitive-357-proof-audit`](https://github.com/bbpcho/primitive-357-proof-audit).

The paper has not been submitted to arXiv.

## Abstract

We prove that the generalized Fermat equation x³+y⁵=z⁷ has no solution in nonzero coprime integers, and we make explicit how the proof extends the prior work it cites. Dahmen–Siksek had established the signed local descent and eliminated the three cases in which the associated degree-seven algebra is reducible. Putz had then proved that the remaining irreducible case can involve only seven septic fields: six pure fields and one exceptional field. The missing step was to exclude those seven fields. For the six pure fields we construct an explicit Fano resolvent, descend to a smooth plane quartic of genus three over Q(√−7), and prove that its rational-parameter locus consists only of five points above the branch values. For the exceptional field we combine the modularity and conductor results of Pacetti–Villagra Torcomian with level lowering over Q(√5) and a finite Hecke comparison at 29. We also reconstruct the three reducible-sector arguments of Dahmen–Siksek as independently replayable calculations. The paper labels every major step as a literature input, reconstructed input, or new argument. All project-specific finite calculations are supplied as exact certificates, programs, inputs, and authenticated logs.

## Contents

| Path | What it is |
| --- | --- |
| [`paper/manuscript.tex`](paper/manuscript.tex), [`paper/rank-proof.tex`](paper/rank-proof.tex) | The paper and its rank appendix (Appendix D). Build with pdfLaTeX; `make paper`. |
| [`paper/manuscript.pdf`](paper/manuscript.pdf) | The compiled paper (41 pages, 22 September 2026). |
| [`release/PRIMITIVE_357_ARXIV_SOURCE_2026-09-22.zip`](release/PRIMITIVE_357_ARXIV_SOURCE_2026-09-22.zip) | The arXiv source upload: exactly the two LaTeX files. |
| [`release/SHA256SUMS.txt`](release/SHA256SUMS.txt) | Digests of every release asset, including the companion. |
| [`release/RELEASE_DELTA_2026-09-22.json`](release/RELEASE_DELTA_2026-09-22.json) | The documents withheld from the companion (see below), with exact identities. |
| [`release/RELEASE_NOTES.md`](release/RELEASE_NOTES.md) | Notes for the release carrying the companion. |

## The computational companion

Release [`replay-companion-2026-09-22.1`](https://github.com/bbpcho/primitive-357/releases/tag/replay-companion-2026-09-22.1) carries `PRIMITIVE_357_REPLAY_COMPANION_2026-09-22_V3.zip` (307 317 706 bytes, SHA-256 `8efa13bdfabb0e7a48bf63f4789e44ce2cd9bac40edb234fdc95f7fecf2bea8c`). Section 8 of the paper describes it. In brief: it stores the project's evidence once, indexed by SHA-256, together with the programs, exact inputs, certificates and the records of a fresh isolated replay of the declared suite — 13 sector/interface records, 65 prior jobs and 16 rank-local checks, the latter joined to five freshly generated inputs.

Verify the download and the distribution:

```sh
sha256sum -c release/SHA256SUMS.txt        # after placing the assets beside it
unzip -q PRIMITIVE_357_REPLAY_COMPANION_2026-09-22_V3.zip
cd PRIMITIVE_357_REPLAY_COMPANION_2026-09-22_V3
python3 -B scripts/verify_companion.py     # exact public file set and logical input mapping
```

The integrity check does not execute the mathematics. A complete arithmetic replay needs SageMath, PARI/GP and the separately acquired inputs; `FINAL_COMPANION_REPLAY_GUIDE.md`, `EXTERNAL_INPUTS_GUIDE.md` and `PROGRAMS_AND_CERTIFICATES.md` inside the archive give the commands, the recorded software versions and the retained imported premises.

Three kinds of material are not redistributed and are acquired separately from pinned sources, authenticated by exact size and SHA-256: the Dahmen–Siksek working paper, the Pacetti–Villagra Torcomian and Bruin–Poonen–Stoll papers, and the unlicensed upstream `GFE-5p3` snapshot; and, since 22 September 2026, the author's own internal working reports, which are author-held inputs of the same lock (`RELEASE_DELTA_2026-09-22.json` lists them). Because their logical paths, byte counts and digests are unchanged, the logical input manifest and the materialized replay tree are identical to those of the recorded replay. The Putz thesis is retained under its CC BY-ND 4.0 notice.

Seven executions through the official Magma calculator (V2.29-10) and four negative controls remain identified, previously executed evidence; the integrated replay does not execute Magma. **This is not proof-assistant certification or external human peer review.** The proof imports the cited mathematical theorems and computer-algebra algorithms; a recorded execution is not an independent implementation of that software.

## Substantial AI-assisted research and writing

OpenAI Codex was used extensively in developing and checking mathematical arguments, computational investigation, program and certificate development, verification design, debugging, release preparation, and drafting and revising the manuscript. OpenAI ChatGPT also supported the research and writing. Anthropic Claude acted as an independent auditor throughout: it reproduced the finite data from published inputs, reviewed every draft, and checked the numbering and content of the cited results against their sources. Its findings led to the database-free identification of Q(√−35), to the model-intrinsic formal-group argument at the prime above 7, and to the scope statement for solutions with a unit coordinate in Section 1; it supplied the characterization of Φ and the derivation of the ramification statement in Section 2; it independently verified the bitangent code data used in Appendix D (the 315 syzygetic tetrads, the rank 21, and the weight enumerator); and it verified the digest, byte count and integrity check of the companion archive and prepared the final arXiv source. Peter Chocian originated the project's discovery approach and research direction, supplied key inputs, reviewed the evidence, and accepts responsibility for all claims. AI-generated suggestions and reviews are not mathematical certificates: the proof rests on the arguments given in the paper, the cited results and the specified computations. These AI-assisted reviews do not constitute independent human peer review or proof-assistant formalization.

## Licence

Original code is MIT licensed; the original paper and documentation are CC BY 4.0. These grants exclude third-party material. See [LICENSE.md](LICENSE.md) and [NOTICE.md](NOTICE.md).
