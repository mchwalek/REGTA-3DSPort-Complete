# Local patch: admit PS2 EE (R5900) ELF32 ET_EXEC into REA's Ghidra lane, pinned to
# the ghidra-emotionengine-reloaded language. Re-run after reinstalling rea-agents.
import subprocess
import sys
from pathlib import Path

# usage: patch_rea_r5900.py [path/to/rea-agents/dist]  (default: global npm install)
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(subprocess.check_output(["npm", "root", "-g"], text=True).strip()) / "rea-agents/dist"
if not root.is_dir():
    sys.exit(f"{root}: not found")
files = sorted(root.glob("mcp/main-*.js")) + sorted(root.glob("cli-runtime/binary-*.js"))

decl_old = "var isGhidraPspTarget, ghidraProcessorUnsupportedReason, GHIDRA_PSP_LIMITATIONS;"
decl_new = decl_old + """
// local patch: PS2 Emotion Engine (EF_MIPS_MACH 0x92 = R5900) via ghidra-emotionengine-reloaded
function isGhidraR5900Target(target) {
\treturn target.kind === "executable" && target.format === "elf" && target.architecture === "mips" && target.mips !== undefined && (target.mips.flags & 16711680) === 9568256;
}"""
gate_old = '\t\t\tif (target.kind !== "executable" || target.architecture !== "mips" || !isGhidraPspTarget(target)) return ghidraMipsUnsupportedReason(target);'
gate_new = ('\t\t\tif (isGhidraR5900Target(target)) return target.mips.elfClass === 32 && target.mips.byteOrder === "little" && target.mips.type === 2 ? null : '
            '"The local R5900 profile supports little-endian ELF32 ET_EXEC only.";\n' + gate_old)
pin_old = "ghidraPinnedLanguage = (target) => ghidraMipsLanguageOverride(target) ??"
pin_new = ('ghidraPinnedLanguage = (target) => (isGhidraR5900Target(target) ? { languageId: "r5900:LE:32:default", compilerSpecId: "default" } : undefined) ?? '
           "ghidraMipsLanguageOverride(target) ??")

for f in files:
    s = f.read_text()
    if "isGhidraR5900Target" in s:
        print(f"{f}: already patched")
        continue
    for old in (decl_old, gate_old, pin_old):
        if s.count(old) != 1:
            sys.exit(f"{f}: expected exactly one match for {old[:60]!r}, found {s.count(old)}")
    s = s.replace(decl_old, decl_new).replace(gate_old, gate_new).replace(pin_old, pin_new)
    f.write_text(s)
    print(f"{f}: patched")
