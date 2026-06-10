#!/usr/bin/env bash
set -euo pipefail

LOG() { echo -e "\n\033[1;34m==>\033[0m $*"; }
OK()  { echo -e "\033[1;32m  ✔ $*\033[0m"; }
WARN(){ echo -e "\033[1;33m  ⚠ $*\033[0m"; }

NIX_FLAGS="--extra-experimental-features nix-command --extra-experimental-features flakes"

LOG "Entering nix dev shell..."
exec nix $NIX_FLAGS develop