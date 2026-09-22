# The Primitive Generalized Fermat Equation x³+y⁵=z⁷

**A computer-assisted proof — Peter Chocian, Independent researcher**

This repository holds the paper proving that `x^3 + y^5 = z^7` has no solution in nonzero coprime integers, its LaTeX source, and the computational companion that makes every project-specific finite calculation replayable. The full audit history of how the proof was reached — snapshots, withdrawn archives and the replacement release of 15 September 2026 — remains in [`bbpcho/primitive-357-proof-audit`](https://github.com/bbpcho/primitive-357-proof-audit).

The paper has not been submitted to arXiv.

## Abstract

We prove that the generalized Fermat equation x³+y⁵=z⁷ has no solution in nonzero coprime integers, and we make explicit how the proof extends the prior work it cites. Dahmen–Siksek had established the signed local descent and eliminated the three cases in which the associated degree-seven algebra is reducible. Putz had then proved that the remaining irreducible case can involve only seven septic fields: six pure fields and one exceptional field. The missing step was to exclude those seven fields. For the six pure fields we construct an explicit Fano resolvent, descend to a smooth plane quartic of genus three over Q(√−7), and prove that its rational-parameter locus consists only of five points above the branch values. For the exceptional field we combine the modularity and conductor results of Pacetti–Villagra Torcomian with level lowering over Q(√5) and a finite Hecke comparison at 29. We also reconstruct the three reducible-sector arguments of Dahmen–Siksek as independently replayable calculations, including their database-free identification of the quadratic field, and add an intrinsic formal-group treatment at the ramified prime. The paper labels every major step as a literature input, reconstructed input, or new argument. All project-specific finite calculations are supplied as exact certificates, programs, inputs, and authenticated logs.

## Contents

| Path | What it is |
| --- | --- |
| [`paper/manuscript.tex`](paper/manuscript.tex), [`paper/rank-proof.tex`](paper/rank-proof.tex) | The paper and its rank appendix (Appendix D). Build with pdfLaTeX; `make paper`. |
| [`paper/manuscript.pdf`](paper/manuscript.pdf) | The compiled paper (43 pages, 23 September 2026). |
| [`release/PRIMITIVE_357_ARXIV_SOURCE_2026-09-23.zip`](release/PRIMITIVE_357_ARXIV_SOURCE_2026-09-23.zip) | The arXiv source upload: exactly the two LaTeX files. |
| [`release/SHA256SUMS.txt`](release/SHA256SUMS.txt) | Digests of every release asset, including the companion and the replay record (the PDF appears under its release filename). |
| [`release/RELEASE_DELTA_2026-09-23.json`](release/RELEASE_DELTA_2026-09-23.json) | Every document removed from the companion, every verifier and record edited, and every file regenerated, with exact identities. |
| [`release/RELEASE_NOTES.md`](release/RELEASE_NOTES.md) | Notes for the release carrying the companion. |
| [`scripts/verify_release.sh`](scripts/verify_release.sh) | Downloads the release assets, checks every digest, extracts the companion and runs its integrity check. |
| [`scripts/build_v4_companion.py`](scripts/build_v4_companion.py) | The tool that derived this companion from the replayed 15 September distribution: removal of the exploratory reports, regeneration of manifest, ledger and certificate metadata, adjustment of pinned row counts, removal of the ten report-artifact checks. |
| [`scripts/preflight_v4.py`](scripts/preflight_v4.py) | Archival static diagnostic used during that derivation (every pinned manifest reference in every archived script and record, classified as failure, historical or unresolved). Not a release gate: the gates are the companion's `verify_companion.py` and `replay_companion.py`. |
| [`release/COMPANION_RUNTIME_NOTES_2026-09-23.md`](release/COMPANION_RUNTIME_NOTES_2026-09-23.md) | Runtime notes that correct the instructions packaged inside the companion (non-interactive launch, PARI/GP 2.15.4, the two recorded runs); also a release asset. |
| [`scripts/build_privatised_companion.py`](scripts/build_privatised_companion.py) | The tool behind the superseded archive of 22 September (withheld reports as author-held inputs); kept as history. |

## The computational companion

Release [`replay-companion-2026-09-23.1`](https://github.com/bbpcho/primitive-357/releases/tag/replay-companion-2026-09-23.1) carries `PRIMITIVE_357_REPLAY_COMPANION_2026-09-23_V4.zip` (298 483 791 bytes, SHA-256 `ecc39d2944092fc2efbfdd17ffe9861e6c1ca68247b06af80bd7bd4bda166c37`; distribution manifest `c376222d…`, logical input manifest `91a2bb027747b6663b5e075d31001e8ee6d12eec3025dd53f86818afffd2ef5d`). Section 8.5 of the paper describes it. In brief: it stores the project's evidence once, indexed by SHA-256, together with the programs, exact inputs, certificates and verification records, and it reconstructs the exact logical input layout (2056 files) for replay from the archive plus 74 separately acquired public inputs.

The same release carries the record of a complete fresh replay of this archive from public material on an independent machine — `PRIMITIVE_357_V4_REPLAY_RECORD_SPARK_2026-09-22.zip` (1 082 797 043 bytes, SHA-256 `dfa8821024c92be9ac509d809a64d529e0072144d420b9164ef6d2f43d8d5295`): Ubuntu 24.04 on aarch64, conda-forge SageMath 10.9 with Python 3.12, PARI/GP 2.15.4 from the Ubuntu package, network access blocked, no access to the author's workspaces. Status `PASS_FRESH_EXTERNALIZED_COMPLETE_REPLAY`: 13 sector/interface records, 65 prior jobs and 16 rank-local checks (the latter joined to five freshly generated inputs), 2562 seconds on 22 September 2026, integrated result digest `e1941808…`, independent envelope `6ad3f186…`. The recorded replay of 15 September (macOS, the recorded SageMath and PARI) reached the same outcome on the replayed distribution.

Verify the download and the distribution — `scripts/verify_release.sh` does all of the following from scratch (add `--with-record` to fetch the replay record as well) — or by hand:

```sh
sha256sum -c release/SHA256SUMS.txt        # after placing the assets beside it
unzip -q PRIMITIVE_357_REPLAY_COMPANION_2026-09-23_V4.zip
cd PRIMITIVE_357_REPLAY_COMPANION_2026-09-23_V4
python3 -B scripts/verify_companion.py     # exact public file set and logical input mapping
```

The integrity check does not execute the mathematics. A complete arithmetic replay needs SageMath, PARI/GP and the separately acquired inputs; `FINAL_COMPANION_REPLAY_GUIDE.md`, `EXTERNAL_INPUTS_GUIDE.md` and `PROGRAMS_AND_CERTIFICATES.md` inside the archive give the commands, the recorded software versions and the retained imported premises. Two requirements observed in the fresh replay: the exact-comparison job `reconstruct_raw66` needs PARI/GP 2.15.4 (2.17 returns equivalent but not byte-identical representatives, and the gate fails by design), and `scripts/replay_companion.py` must be launched with standard input detached from a terminal (`< /dev/null`), since one negative-control job otherwise waits at gp's interactive prompt.

Relative to the replayed distribution `replay-companion-2026-09-15.2`, this archive removes 72 exploratory working reports — narrative documents that are inputs of no executed calculation — and regenerates the manifests, indices, ledgers and certificates that recorded their digests; ten verifiers that certified their own narrative report as an artifact no longer do so, and every pinned manifest row count is adjusted by the corresponding removal. No mathematical acceptance predicate, exact arithmetic input or certified mathematical value changed; certificate and ledger metadata (pinned digests, row counts, report-artifact fields) is regenerated. `release/RELEASE_DELTA_2026-09-23.json` lists every removed document, every edited verifier and record, and every regenerated file. It supersedes `replay-companion-2026-09-22.1`, which withheld the same class of documents as author-held inputs and therefore could not be replayed from public material.

Three kinds of material are not redistributed and are acquired separately from pinned sources, authenticated by exact size and SHA-256: the Dahmen–Siksek working paper, the Pacetti–Villagra Torcomian and Bruin–Poonen–Stoll papers, and the unlicensed upstream `GFE-5p3` snapshot. The Putz thesis is retained under its CC BY-ND 4.0 notice.

Seven executions through the official Magma calculator (V2.29-10) and four negative controls remain identified, previously executed evidence; the integrated replay does not execute Magma. **This is not proof-assistant certification or external human peer review.** The proof imports the cited mathematical theorems and computer-algebra algorithms; a recorded execution is not an independent implementation of that software.

## Substantial AI-assisted research and writing

OpenAI Codex was used extensively in developing and checking mathematical arguments, computational investigation, program and certificate development, verification design, debugging, release preparation, and drafting and revising the manuscript. OpenAI ChatGPT also supported the research and writing. Anthropic Claude acted as an independent auditor throughout: it reproduced the finite data from published inputs, reviewed every draft, and checked the numbering and content of the cited results against their sources. Its findings led to the model-intrinsic formal-group argument at the prime above 7 and to the scope statement for solutions with a unit coordinate in Section 1, and it reconstructed Dahmen–Siksek's database-free identification of Q(√−35) as a certified calculation (an earlier draft wrongly credited that identification as new; the error was found in pre-submission review); it supplied the characterization of Φ and the derivation of the ramification statement in Section 2; it independently verified the bitangent code data used in Appendix D (the 315 syzygetic tetrads, the rank 21, and the weight enumerator); it verified the digest, byte count and integrity check of the companion archive and prepared the final arXiv source; and it built the public companion of 23 September and the tooling that adjusted its ledgers, whose fresh replay from public material was run by the author. Peter Chocian originated the project's discovery approach and research direction, supplied key inputs, reviewed the evidence, and accepts responsibility for all claims. AI-generated suggestions and reviews are not mathematical certificates: the proof rests on the arguments given in the paper, the cited results and the specified computations. These AI-assisted reviews do not constitute independent human peer review or proof-assistant formalization.

## Licence

Original code is MIT licensed; the original paper and documentation are CC BY 4.0. These grants exclude third-party material. See [LICENSE.md](LICENSE.md) and [NOTICE.md](NOTICE.md).
