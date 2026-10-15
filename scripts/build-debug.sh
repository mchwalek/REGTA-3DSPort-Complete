#!/bin/sh
# Debug build of reLCS: compiles in the pad-driven debug menu
# (toggle: R + B + D-pad Up). Output still lands at stories/build/relcs.3dsx,
# overwriting any release build there. See the relcs-3ds-build skill and
# README.md for details on the debug menu itself.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

DEBUGMENU=1 exec "$script_dir/build.sh" relcs
