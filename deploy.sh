#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
hosttools="$script_dir/../hosttools/3dslink"

game=${1:?specify a game: re3|revc|relcs}
ip=${2:-${N3DS_IP:?set N3DS_IP or pass the 3DS IP as the second argument}}

case "$game" in
	re3|III|iii)
		name=re3
		built="$script_dir/III/build/re3.3dsx"
		;;
	revc|vc|miami)
		name=revc
		built="$script_dir/miami/build/miami.3dsx"
		;;
	relcs|lcs|stories)
		name=relcs
		built="$script_dir/stories/build/relcs.3dsx"
		;;
	*)
		echo "Unknown game: $game" >&2
		echo "Usage: ./deploy.sh <re3|revc|relcs> [3ds-ip]" >&2
		echo "3ds-ip defaults to \$N3DS_IP if not given." >&2
		exit 2
		;;
esac

[ -x "$hosttools" ] || {
	echo "3dslink not found at $hosttools" >&2
	echo "See the relcs-3ds-build skill for how to build it." >&2
	exit 3
}

[ -f "$built" ] || {
	echo "Build output is missing: $built" >&2
	echo "Run scripts/build.sh $name first." >&2
	exit 3
}

echo "Deploying $built to $ip ..." >&2
exec "$hosttools" -a "$ip" "$built"
