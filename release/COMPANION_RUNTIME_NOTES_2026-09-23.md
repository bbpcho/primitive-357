# Runtime notes for PRIMITIVE_357_REPLAY_COMPANION_2026-09-23_V4.zip

These notes correct and complete the runtime instructions packaged inside the
companion (`README.md` at the archive root and `RUNTIMES.md` in the logical
tree). Those two files are not edited in place: the archive's identity
(SHA-256 ecc39d29…, distribution manifest c376222d…, logical input manifest
91a2bb02…) is bound to the published replay record, and a documentation-only
re-issue would break that binding. The paper (Section 8.5) and the repository
README carry the same information.

1. **Launch non-interactively.** The replay command in the companion's
   `README.md` must be run with standard input detached from a terminal:
   append `< /dev/null`. One negative-control job (`altered_conic` in
   `p5_precision_and_negative_controls`) ends with a deliberate `gp` error
   before its `quit`; with a terminal on standard input the readline-linked
   Ubuntu `gp` waits at its prompt until the job's 300-second limit kills it.

2. **PARI/GP 2.15.4 exactly.** The exact-comparison job `reconstruct_raw66`
   compares freshly computed dyadic coordinates byte for byte with a frozen
   matrix. PARI 2.17 returns equivalent but not byte-identical representatives
   and the gate fails by design. On Ubuntu 24.04 the packaged `pari-gp` is
   2.15.4; pass its `gp` with `--gp`.

3. **Two recorded runs, not one.** The companion's `RUNTIMES.md` describes the
   recorded macOS replay of 15 September (SageMath 10.9, PARI/GP 2.15.4) and
   states that no fresh Linux run is claimed there. Superseding that
   statement, the published record
   `PRIMITIVE_357_V4_REPLAY_RECORD_SPARK_2026-09-22.zip` (SHA-256 dfa88210…)
   is a complete fresh replay of this archive on Ubuntu 24.04 (aarch64) with
   conda-forge SageMath 10.9, Python 3.12 and the Ubuntu PARI/GP 2.15.4:
   `PASS_FRESH_EXTERNALIZED_COMPLETE_REPLAY`, 13 sector/interface records,
   65 prior jobs, 16 rank-local checks, 2562 s on 22 September 2026. The
   macOS run applies to the replayed distribution of 15 September; the Linux
   run applies to this archive.

4. **Isolation.** The driver requires an external isolation boundary
   (network disabled, no access to earlier proof workspaces). The record
   documents the run inside that boundary; it does not capture the boundary's
   own set-up. The published Linux run used `unshare -n` on a host with no
   copy of the author's workspaces.
