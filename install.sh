#!/usr/bin/env bash
# Convenience wrapper so a clone of this repo can install into a project without the plugin:
#   ./install.sh /path/to/project      ./install.sh --user      ./install.sh --dry-run /path/to/project
# The real installer lives inside the plugin so /eng:setup can run it too.
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/plugins/eng/install.sh" "$@"
