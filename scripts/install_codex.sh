#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir="$repo_dir/assets/codex/tokage"
target_dir="${CODEX_HOME:-$HOME/.codex}/pets/tokage"

if [ ! -f "$source_dir/pet.json" ] || [ ! -f "$source_dir/spritesheet.webp" ]; then
  echo "Codex pet package is incomplete: $source_dir" >&2
  exit 2
fi

if [ -e "$target_dir" ]; then
  printf 'Target already exists: %s\nReplace it? [y/N] ' "$target_dir"
  read -r answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "Cancelled."; exit 1 ;;
  esac
fi

mkdir -p "$target_dir"
cp "$source_dir/pet.json" "$target_dir/pet.json"
cp "$source_dir/spritesheet.webp" "$target_dir/spritesheet.webp"
echo "Installed Tokage into $target_dir"

