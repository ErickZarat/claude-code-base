#!/usr/bin/env bash
# Installs or updates the eng-standards project files (rules, CLAUDE.md, settings, pre-commit config).
# Skills, agents and the secret-guard hook come from the plugin itself — this script only handles the
# files Claude Code plugins cannot distribute.
#
# Usage:
#   install.sh [--dry-run] [PROJECT_DIR]   project install/update (default: current directory)
#   install.sh [--dry-run] --user          rules only, into ~/.claude (apply to every project)
#
# Update safety: a manifest records the checksum of every managed file as installed.
#   - unchanged locally  -> replaced with the new version
#   - modified locally   -> kept; the new version is written next to it as <file>.eng-new for manual merge
#   - seed files (CLAUDE.md, settings.json) are only created, never overwritten
#   - paths listed in .claude/.eng-standards-ignore (e.g. .claude/rules/lang/python.md) are never installed
#
# Compatible with macOS's bash 3.2.

set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$PLUGIN_DIR/template"
PLUGIN_VERSION="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$PLUGIN_DIR/.claude-plugin/plugin.json")"

MANAGED_PATHS=(".claude/rules" ".pre-commit-config.yaml")
SEED_PATHS=("CLAUDE.md" ".claude/settings.json")
GITIGNORE_ENTRIES=(".env" ".env.*" "!.env.example" "CLAUDE.local.md" ".claude/settings.local.json" "*.eng-new")

dry_run=false
user_mode=false
target_dir="$PWD"

created=() updated=() unchanged=() conflicts=() seeded_skip=() ignored=()

file_checksum() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

# Prints the checksum recorded for a relative path in the previous manifest, or nothing.
recorded_checksum() {
  local relative_path="$1"
  [[ -f "$old_manifest" ]] || return 0
  awk -v path="$relative_path" '$2 == path { print $1 }' "$old_manifest"
}

write_file() {
  local source_file="$1" destination_file="$2"
  $dry_run && return 0
  mkdir -p "$(dirname "$destination_file")"
  cp "$source_file" "$destination_file"
}

# Lists template files under a managed path, relative to the template root.
template_files_under() {
  local managed_path="$1"
  if [[ -d "$TEMPLATE_DIR/$managed_path" ]]; then
    (cd "$TEMPLATE_DIR" && find "$managed_path" -type f | sort)
  elif [[ -f "$TEMPLATE_DIR/$managed_path" ]]; then
    echo "$managed_path"
  fi
}

# True when the project opted out of a managed file (one path or directory prefix per line in the ignore file).
is_ignored() {
  local relative_path="$1" ignored_path
  [[ -f "$ignore_file" ]] || return 1
  while IFS= read -r ignored_path; do
    ignored_path="${ignored_path%%#*}"; ignored_path="${ignored_path%"${ignored_path##*[![:space:]]}"}"
    [[ -z "$ignored_path" ]] && continue
    [[ "$relative_path" == "$ignored_path" || "$relative_path" == "$ignored_path"/* ]] && return 0
  done < "$ignore_file"
  return 1
}

sync_managed_file() {
  local relative_path="$1"
  if is_ignored "$relative_path"; then
    ignored+=("$relative_path")
    return
  fi
  local template_file="$TEMPLATE_DIR/$relative_path"
  local target_file="$target_dir/$relative_path"
  local new_checksum previous_checksum current_checksum
  new_checksum="$(file_checksum "$template_file")"

  if [[ ! -e "$target_file" ]]; then
    write_file "$template_file" "$target_file"
    created+=("$relative_path")
    echo "$new_checksum $relative_path" >> "$new_manifest"
    return
  fi

  current_checksum="$(file_checksum "$target_file")"
  previous_checksum="$(recorded_checksum "$relative_path")"

  if [[ "$current_checksum" == "$new_checksum" ]]; then
    unchanged+=("$relative_path")
    echo "$new_checksum $relative_path" >> "$new_manifest"
  elif [[ -n "$previous_checksum" && "$current_checksum" == "$previous_checksum" ]]; then
    write_file "$template_file" "$target_file"
    updated+=("$relative_path")
    echo "$new_checksum $relative_path" >> "$new_manifest"
  else
    write_file "$template_file" "$target_file.eng-new"
    conflicts+=("$relative_path")
    # Keep the old record so the file is still recognised as locally modified next time.
    [[ -n "$previous_checksum" ]] && echo "$previous_checksum $relative_path" >> "$new_manifest"
  fi
}

seed_file() {
  local relative_path="$1"
  if [[ -e "$target_dir/$relative_path" ]]; then
    seeded_skip+=("$relative_path")
  else
    write_file "$TEMPLATE_DIR/$relative_path" "$target_dir/$relative_path"
    created+=("$relative_path")
  fi
}

append_gitignore_entries() {
  local gitignore_file="$target_dir/.gitignore" entry
  $dry_run && return 0
  touch "$gitignore_file"
  for entry in "${GITIGNORE_ENTRIES[@]}"; do
    grep -qxF -- "$entry" "$gitignore_file" || echo "$entry" >> "$gitignore_file"
  done
}

print_group() {
  local title="$1"; shift
  (( $# == 0 )) && return 0
  echo "$title"
  printf '  %s\n' "$@"
}

while (( $# > 0 )); do
  case "$1" in
    --dry-run) dry_run=true ;;
    --user) user_mode=true ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) target_dir="$1" ;;
  esac
  shift
done

if $user_mode; then
  target_dir="$HOME"
  MANAGED_PATHS=(".claude/rules")
  SEED_PATHS=()
fi
[[ -d "$target_dir" ]] || { echo "Not a directory: $target_dir" >&2; exit 1; }
target_dir="$(cd "$target_dir" && pwd)"

old_manifest="$target_dir/.claude/.eng-standards-manifest"
ignore_file="$target_dir/.claude/.eng-standards-ignore"
new_manifest="$(mktemp)"
trap 'rm -f "$new_manifest"' EXIT

for managed_path in "${MANAGED_PATHS[@]}"; do
  while IFS= read -r relative_path; do
    sync_managed_file "$relative_path"
  done < <(template_files_under "$managed_path")
done
for seed_path in ${SEED_PATHS[@]+"${SEED_PATHS[@]}"}; do
  seed_file "$seed_path"
done

if ! $dry_run; then
  mkdir -p "$target_dir/.claude"
  sort -k2 "$new_manifest" > "$old_manifest"
  echo "$PLUGIN_VERSION" > "$target_dir/.claude/.eng-standards-version"
  $user_mode || append_gitignore_entries
fi

$dry_run && echo "[dry run — nothing written]"
echo "eng-standards $PLUGIN_VERSION -> $target_dir"
print_group "Created:" ${created[@]+"${created[@]}"}
print_group "Updated:" ${updated[@]+"${updated[@]}"}
print_group "Locally modified — kept yours, new version saved as <file>.eng-new (merge, then delete it):" \
  ${conflicts[@]+"${conflicts[@]}"}
print_group "Project-owned, left untouched:" ${seeded_skip[@]+"${seeded_skip[@]}"}
print_group "Skipped (listed in .claude/.eng-standards-ignore):" ${ignored[@]+"${ignored[@]}"}
echo "Up to date: ${#unchanged[@]} file(s)"
