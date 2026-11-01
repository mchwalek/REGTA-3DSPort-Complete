#!/usr/bin/env python3
"""Regenerate gamefiles/relcs/DATA/WEAPON.DAT from PS2 LCS's compiled weapon table.

PS2 has no text weapon.dat; the table is compiled into /CHK/PS2/GAME.DTZ.
Pass the *decompressed* GAME.DTZ (copyrighted, keep it outside the repo).
Row order and names are taken from the existing WEAPON.DAT; only values change.

    python3 scripts/ps2_weapon_dat.py /path/to/GAME.DTZ.dec gamefiles/relcs/DATA/WEAPON.DAT
"""
import struct
import sys

TABLE = 0x40a980  # EUR SLES_541.35 GAME.DTZ, decompressed
STRIDE = 0x70
FIRE = ["MELEE", "INSTANT_HIT", "PROJECTILE", "AREA_EFFECT", "CAMERA"]
# index = position in stories/src/animation/AnimManager.cpp's aStdAnimGroups
GROUPS = ["man", "van", "coach", "bikes", "bikev", "bikeh", "biked", "unarmed", "screwdrv", "knife", "baseball", "golfclub",
	  "chainsaw", "python", "colt45", "shotgun", "buddy", "tec", "uzi", "rifle", "m60", "sniper", "grenade", "flame", "rocketla"]


def f(x):
	return ("%.4f" % x).rstrip("0").rstrip(".")


def row(data, i):
	w = struct.unpack_from("<28I", data, TABLE + i * STRIDE)
	fl = struct.unpack_from("<28f", data, TABLE + i * STRIDE)
	sint = lambda v: v - (1 << 32) if v & 0x80000000 else v
	frames = [round(fl[k] * 30) for k in range(17, 24)]
	return [FIRE[w[0]], "%.1f" % fl[1], w[2], w[3], w[4], w[5]] + [f(fl[k]) for k in (6, 7, 8, 9, 12, 13, 14)] + \
	       [GROUPS[w[16]]] + frames + [sint(w[24]), sint(w[25]), "%X" % w[27], w[26]]


def main(src, dat):
	data = open(src, "rb").read()
	lines = open(dat).read().split("\n")
	out, i = [], 0
	for line in lines:
		if line.strip() and not line.startswith("#") and line.strip() != "ENDWEAPONDATA":
			old = line.split()
			new = row(data, i)
			# keep port melee flags: PS2 sets CANAIM bits on melee, which reLCS's aim code treats as guns
			if new[0] == "MELEE":
				new[-2] = old[-2]
			out.append("\t".join([old[0].ljust(15)] + [str(v) for v in new]))
			i += 1
		else:
			out.append(line)
	# self-check: PS2 Shotgun row must equal the long-standing (correct) port row
	assert row(data, 19) == ["INSTANT_HIT", "40.0", 250, 450, 1, 80, "-1", "-1", "-1", "-1", "0.86", "-0.02", "0.28",
				 "shotgun", 12, 34, 15, 9, 26, 13, 30, 277, -1, "20040", 4], row(data, 19)
	assert i == 37, i
	open(dat, "w").write("\n".join(out))


if __name__ == "__main__":
	main(*sys.argv[1:3])
