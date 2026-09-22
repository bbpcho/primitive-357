# Release notes — replay-companion-2026-09-22.1

This release supersedes `replay-companion-2026-09-15.2` of the audit archive `bbpcho/primitive-357-proof-audit`. The computational
companion `PRIMITIVE_357_REPLAY_COMPANION_2026-09-22_V3.zip` (307 317 706
bytes, SHA-256 8efa13bd…) differs from the replayed distribution in one way:
the author's internal working reports are no longer redistributed. They are
author-held inputs of the dependency lock, with unchanged logical paths, byte
counts and SHA-256 digests, so `RELEASE_MANIFEST.json` and the materialized
replay tree are identical to those of the recorded fresh replay (13
sector/interface records, 65 prior jobs, 16 rank-local checks). The file
`RELEASE_DELTA_2026-09-22.json` lists every such document. The public
integrity check and the public-contents scan pass; a full private
materialization from this archive reproduces the replayed tree. The revised
paper prints this archive's identity in Section 8.5, includes a scope
statement for solutions with a unit coordinate, the characterization of the
descent polynomial and the ramification derivation in Section 2, and an
updated AI-assistance statement.

