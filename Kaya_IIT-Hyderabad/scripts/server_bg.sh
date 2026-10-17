#!/usr/bin/env bash
# Long-running server jobs, run detached: dataset download and Python requirements install.
# Usage: bash scripts/server_bg.sh <cgmacros|pip>
set -uo pipefail
ROOT="${KAYA_ROOT:-$HOME/kaya}"
cd "$ROOT"
case "${1:-}" in
  cgmacros)
    U=https://physionet-open.s3.amazonaws.com/cgmacros/1.0.0
    mkdir -p data/raw/cgmacros && cd data/raw/cgmacros
    for f in LICENSE.txt SHA256SUMS.txt DataDictionary.pdf DataDictionary_Bio.csv \
             DataDictionary_CGMacros-00X.csv CGMacros_dateshifted365.zip; do
      wget -c -q "$U/$f" || echo "FAILED $f"
    done
    echo FINISHED > DONE
    ;;
  pip)
    MIRROR="${PIP_INDEX:-https://pypi.org/simple}"
    .venv/bin/python -m pip install -i "$MIRROR" -r requirements.txt && echo FINISHED > pip.DONE
    ;;
esac
