#!/usr/bin/env bash
# Verify the published release of the computational companion from scratch.
# Copyright (c) 2026 Peter Chocian. MIT.
#
# Downloads every asset of the release, checks the digests against the
# release's own SHA256SUMS.txt, confirms the companion's identity printed in
# the paper, extracts the companion into a fresh directory and runs its
# distribution integrity check. Needs curl, sha256sum, unzip and python3.
#
# Usage: scripts/verify_release.sh [WORKDIR]   (default: ./release-verify)
set -euo pipefail

REPO="bbpcho/primitive-357"
TAG="replay-companion-2026-09-22.1"
COMPANION="PRIMITIVE_357_REPLAY_COMPANION_2026-09-22_V3.zip"
COMPANION_SHA256="8efa13bdfabb0e7a48bf63f4789e44ce2cd9bac40edb234fdc95f7fecf2bea8c"
COMPANION_BYTES=307317706
ASSETS=("$COMPANION" "PRIMITIVE_357_ARXIV_SOURCE_2026-09-22.zip" \
        "primitive_357_peter_chocian_2026_09_22.pdf" "RELEASE_DELTA_2026-09-22.json" "SHA256SUMS.txt")

WORK="${1:-release-verify}"
mkdir -p "$WORK" && cd "$WORK"

echo "== downloading ${#ASSETS[@]} assets of $REPO release $TAG"
for f in "${ASSETS[@]}"; do
  curl -fsSL -o "$f" "https://github.com/$REPO/releases/download/$TAG/$f"
done

echo "== digests against the release ledger"
sha256sum -c SHA256SUMS.txt

echo "== companion identity as printed in the paper (Section 8.5)"
size=$(wc -c < "$COMPANION" | tr -d ' ')
sum=$(sha256sum "$COMPANION" | cut -d' ' -f1)
[ "$size" = "$COMPANION_BYTES" ] || { echo "size mismatch: $size"; exit 1; }
[ "$sum" = "$COMPANION_SHA256" ] || { echo "digest mismatch: $sum"; exit 1; }
echo "OK: $COMPANION_BYTES bytes, SHA-256 $COMPANION_SHA256"

echo "== companion integrity check on a fresh extraction"
rm -rf extracted && mkdir extracted
unzip -q "$COMPANION" -d extracted
( cd "extracted/${COMPANION%.zip}" && python3 -B scripts/verify_companion.py )

echo "== arXiv source archive contains exactly the two LaTeX files"
unzip -Z1 PRIMITIVE_357_ARXIV_SOURCE_2026-09-22.zip | sort | diff - <(printf 'manuscript.tex\nrank-proof.tex\n')
echo "OK"
echo "== all checks passed"
