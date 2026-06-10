#!/usr/bin/env bash
set -euo pipefail

LOG() { echo -e "\n\033[1;34m==>\033[0m $*"; }
OK()  { echo -e "\033[1;32m  ✔ $*\033[0m"; }
WARN(){ echo -e "\033[1;33m  ⚠ $*\033[0m"; }

LOG "Installing Nix..."
if command -v nix &>/dev/null; then
  WARN "Nix already installed ($(nix --version)), skipping."
else
  sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --daemon
  OK "Nix installed"

  if [ -f /etc/profile.d/nix.sh ]; then
    . /etc/profile.d/nix.sh
  elif [ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
    . "$HOME/.nix-profile/etc/profile.d/nix.sh"
  fi
fi