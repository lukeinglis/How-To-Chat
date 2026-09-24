#!/usr/bin/env bash
# Downloads external eval datasets into data/external/ (gitignored).
# Eval only. Never train on these. See data/sources.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXT="$ROOT/data/external"
mkdir -p "$EXT"

clone() {
  local url="$1" dir="$2"
  if [ -d "$EXT/$dir/.git" ]; then
    echo "✓ $dir already present"
  else
    echo "→ cloning $dir"
    git clone --depth 1 "$url" "$EXT/$dir"
  fi
}

clone https://github.com/meg-tong/sycophancy-eval.git sharma
clone https://github.com/myracheng/elephant.git elephant
clone https://github.com/myracheng/accommodation.git accommodation

cat <<'EOF'

Manual downloads (not scriptable without accounts or tokens):

1. ELEPHANT full datasets
   https://osf.io/r3dmj/?view_only=37ee66a8020a45c29a38bd704ca61067
   Download datasets.zip, unzip into data/external/elephant/datasets/

2. Phare public set
   pip install huggingface_hub
   huggingface-cli download giskardai/phare --repo-type dataset --local-dir data/external/phare

3. Perez sycophancy
   huggingface-cli download Anthropic/model-written-evals --repo-type dataset \
     --include "sycophancy/*" --local-dir data/external/perez
EOF
