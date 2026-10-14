#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
workspace_root=$(CDPATH= cd -- "$project_root/.." && pwd)

: "${BANNERTOOL:=$workspace_root/hosttools/bannertool}"
: "${MAKEROM:=$workspace_root/hosttools/makerom}"
: "${THREEDSXTOOL:=${DEVKITPRO:-$workspace_root/sdk-r55}/tools/bin/3dsxtool}"
export BANNERTOOL MAKEROM THREEDSXTOOL

normalize_game()
{
	case "$1" in
		re3|III|iii) echo re3 ;;
		revc|vc|miami) echo revc ;;
		relcs|lcs|stories) echo relcs ;;
		*)
			echo "Unknown game: $1" >&2
			echo "Usage: scripts/package-cia.sh [re3|revc|relcs ...]" >&2
			echo "No args packages all three (each needs its ELF already built)." >&2
			exit 2
			;;
	esac
}

games=""
for arg in "$@"; do
	games="$games $(normalize_game "$arg")"
done

# $games is intentionally unquoted: empty means "package everything",
# matching build_production.sh's own default.
exec "$project_root/packaging/production_cia/build_production.sh" $games
