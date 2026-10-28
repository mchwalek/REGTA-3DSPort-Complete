---
name: ps2-lcs-decompilation
description: Extract and reverse-engineer the original PS2 GTA Liberty City Stories disc (SLES_541.35 boot ELF, main.scm, ISO9660 filesystem) to establish authoritative ground truth for behavior questions in the reLCS 3DS port. Use when the user asks "what does the original/PS2 game actually do", questions a value/colour/constant/behavior against the real game, provides or references a PS2 LCS ISO, asks to decompile/disassemble/RE the PS2 binary (incl. Ghidra/REA pseudocode of a PS2 function), or when reLCS source appears to have inherited a wrong value from its Vice City ancestor and no fork/decompilation project has already fixed it.
---

# PS2 LCS decompilation

reLCS (`stories/`) is a from-scratch reimplementation, not a decompilation —
it was bootstrapped from reVC (`miami/`) and inherited some VC-specific
constants/behavior that were never corrected for LCS (see the 3D-marker
arrow-colour case study below, a textbook example: the pink arrow color was
literally copy-pasted from Vice City into every public reLCS fork on GitHub,
including reference forks like `knackers4/res`, because nobody had ever
checked it against the real PS2 game).

**When public source forks don't have the answer, the PS2 disc does.** This
skill covers extracting and disassembling it.

## When source archaeology isn't enough

Before reaching for the ISO, exhaust the cheap options: `git log` on the
suspect files, `grep` for the constant across public re3/reVC/reLCS forks via
`gh search code`, and check whether the "obviously wrong" value is actually
shared verbatim by VC (a strong signal it's inherited, not LCS-original — see
`stories/src/core/Radar.h`'s `MARKER_COLOR_*` history for a real example).
Only reach for the disc once you've confirmed no existing project has already
resolved the question.

## Tools

All scripts live in `scripts/` next to this file and have no dependency on
this repo's build system — they're standalone Python, run from any directory
once you pass full paths (or `cd` into `scripts/` so the plain
`import elf_tools` works). Only third-party dependency: `pip install
capstone` for disassembly (extraction and data-table reads work without it).

### `scripts/iso9660.py` — extract files from the disc

The disc is plain ISO9660 (no RockRidge/Joliet needed for PS2 discs).

```sh
python3 scripts/iso9660.py list   "/path/to/GTA LCS (EUR).iso"
python3 scripts/iso9660.py extract "/path/to/GTA LCS (EUR).iso" /SLES_541.35 $WORKSPACE_ROOT/sre/SLES_541.35
python3 scripts/iso9660.py extract "/path/to/GTA LCS (EUR).iso" /DATA/MAIN.SCM /tmp/main.scm
```

Known layout of the EUR LCS disc: boot ELF at `/SLES_541.35` (~2.99 MB),
script at `/DATA/MAIN.SCM`, text at `/TEXT/ENGLISH.GXT`, models in
`/MODELS/*.IMG`. Other regions/revisions will have a different serial
number but the same rough layout — `list` first to confirm.

### `scripts/elf_tools.py` — load and disassemble the boot ELF

The boot ELF is a stripped, statically-linked MIPS III (PS2 "Emotion Engine")
executable. Section headers and the linker `$gp` value (needed for
`lw $t0,-0x828($gp)`-style loads — the EE's small-data-area addressing) are
parsed directly from the ELF, not hardcoded, so this works across disc
revisions without editing the script.

```python
import sys; sys.path.insert(0, 'scripts')
import elf_tools as E
import os; E.load(os.path.expandvars('$WORKSPACE_ROOT/sre/SLES_541.35'))
E.gp                          # linker $gp, e.g. 0x3d70f0
E.dis(0x118380, 60)           # disassemble 60 insns at a VA (needs capstone)
E.words(0x3cf9c8, 4)          # read raw data words (jump tables, const tables)
E.find_addr_refs(0x3cf9c8)    # VAs of `lui;<imm-op>` pairs that build this address
```

CLI form: `python3 elf_tools.py <elf> dis|words|refs <hexva> [count]`.

**`dis_robust()`/CLI `dis`** must be used over plain `dis()` for anything
beyond a quick peek: the PS2 EE has 128-bit MMI/COP2 instructions capstone's
plain MIPS32 mode can't decode, and it will simply stop at the first one.
`dis_robust` prints `.word 0x...` for those and keeps going.

**`find_addr_refs(target)`** is how you find *who references* a data address
in a binary with no relocation table left — e.g. "what code reads this RGBA
colour constant". It only catches the `lui $rt,HI16` + (`addiu`|`ori`|load/store)
`$rt,LO16($rt)` pattern; gp-relative loads (`lw $t0,IMM($gp)`) need a
different scan (grep disassembly output for `($gp)` near the byte offset you
computed from `target - gp`) since there's no `lui` to anchor on.

### `scripts/scm_disasm.py` — disassemble `main.scm`

Parses the opcode table straight from `stories/src/control/ScriptDebug.cpp`'s
`REGISTER_COMMAND` macros (so it always matches whatever opcode set this port
implements) and decodes self-describing parameters per the `ARGUMENT_*`
scheme in `stories/src/control/Script.h`.

```python
import scm_disasm as S
names, args = S.load_opcode_table('/path/to/stories/src/control/ScriptDebug.cpp')
d = S.load_scm('/path/to/main.scm')
start = S.first_instruction_offset(d)   # script always opens with a GOTO past the mission table
for opname, params, nexti in S.disasm_linear(d, names, args, start):
    print(opname, params)
```

**Only trust linear disassembly from a known-good anchor** (offset 0's GOTO
target). SCM opcodes have no alignment/sync markers, so scanning forward from
an arbitrary offset and trying to "validate" a candidate stream is unreliable
— it produced both false negatives and false positives when tried (see the
case study). If you need to read at an arbitrary offset, decode linearly from
the nearest confirmed instruction boundary, not from the target offset
directly.

**Known limitation:** `load_opcode_table()`'s argument lists come from
`ScriptDebug.cpp`'s `REGISTER_COMMAND` table, which is inherited from reVC and
is *wrong* for a nontrivial number of LCS-only opcodes (wrong arg count or
wrong types) — `disasm_linear` will desync a few instructions after any such
opcode. If you hit a desync, don't assume the anchor was wrong; check whether
the offending opcode's actual argument count (derived from its C++ `case`
body: `CollectParameters`/`StoreParameters` counts, `GetPointerToScriptVariable`
calls, `ReadTextLabelFromScript` = 8 bytes each) matches what
`ScriptDebug.cpp` claims before concluding the anchor or decoder is broken.

**Opcode numbering:** `load_opcode_table()` drops the `#ifdef
SUPPORT_GINPUT_SCRIPT` arm (`COMMAND_HAS_PAD_IN_HANDS`) of `ScriptDebug.cpp`.
Before that fix every opcode from ~297 on was off by one (it reported
`ADD_ONE_OFF_SOUND` as 0x192; the real value is 0x191). If another `#ifdef`
pair is added to the table, sanity-check a known opcode: `SCRIPT_NAME` must be
0x3a9.

**`COMMAND_CALL`/`CALLNOT` (0x5ae, `Script8.cpp`) aren't decoded by the arg
table.** Layout: opcode, 3 raw bytes (`nInputParams`, `nOutputParams`,
`localsOffset`), one self-describing target param, then `nInputParams`
params. `disasm_linear` desyncs at the first CALL unless you special-case it.
To find a named script, search for its 8-byte name: the `SCRIPT_NAME`
instruction starts 2 bytes before it.

#### `main.scm` binary layout (verified against the real file)

- Raw file starts with an 8-byte header: `uint32 MainScriptSize`, `uint32
  LargestMissionSize`. `load_scm()` strips these 8 bytes, so offset 0 in its
  returned bytes is ScriptSpace offset 0 (what GOTO/JSR targets are relative
  to) — **not** the raw file offset.
- **Mission table**: at raw file offset `MainScriptSize + 8 + 20`, preceded
  by `uint32 LargestMissionSize` (repeated) and `uint32 missionCount`. Table
  is `missionCount` `uint32` entries, each one a **ScriptSpace offset** for
  that mission's code. (This did not match the EUR file during the
  Karmageddon investigation; the authoritative walk is
  `ReadMultiScriptFileOffsetsFromScript` in `stories/src/control/Script5.cpp`.
  Finding a mission by its 8-byte `SCRIPT_NAME` is simpler.)
- **UsedObjectArray**: negative model ids in script params (`INT8 0x94` = -108)
  index a table of 24-byte names. In the EUR file it starts right after an
  `int32` count (297) just before raw offset `0x489e`. Entry 0 is empty.
- **Raw-file offset of mission `i`'s code**: `table[i] + 8 + local_offset`
  (the `+8` re-adds the header that `load_scm()`/ScriptSpace strips — do not
  forget it when seeking in the *raw* file, as opposed to indexing into
  `load_scm()`'s returned bytes, which need no adjustment).
- **Runtime `m_nIp` for mission code**: `MainScriptSize + local_offset`
  (mission bytecode is loaded starting right after the main script in
  `ScriptSpace`).
- Opcodes are 2 bytes little-endian; bit `0x8000` is the NOT flag (strip it
  before indexing `names`/`args`). `CRunningScript::ProcessOneCommand`
  dispatches to `ProcessCommandsXToY` in bins of the form `<100, <200, <305,
  <405, ...` — note the bin width creeps by 5 starting at 300, it is not a
  uniform `<(N+100)`.
- Parameter type-byte payload widths (`ARGUMENT_*` in `Script.h`, verified
  against `CollectParameters`): END/INT_ZERO/FLOAT_ZERO = 0 bytes;
  FLOAT_1BYTE=1; FLOAT_2BYTES=2; FLOAT_3BYTES=3; INT32/FLOAT=4; INT8=1;
  INT16=2; TIMER=0; LOCAL=0; **LOCAL_ARRAY=2** extra bytes (index_id, size);
  **GLOBAL=1** extra byte (global index low byte); GLOBAL_ARRAY=3 extra
  bytes (index_in_block, index_id, size). `ARGTYPE_STRING`/`ARGTYPE_TEXT_LABEL`
  parameters (not encoded via the type-byte scheme) are a fixed 8 raw bytes.
- `first_instruction_offset()`'s target is itself a self-describing param
  (type byte + payload), not a bare int32 immediately after the opcode —
  decode it with `_read_param`, the same as any other instruction operand.

These facts (and the `first_instruction_offset`/`LOCAL_ARRAY`/`GLOBAL` byte-
width bugs they exposed) came from reverse-engineering the TR1 ("Wong Side of
the Tracks") mission-23 spawn-loop crash; see `git log --grep=TR1` /
`--grep="Wong Side"` for the investigation if more script-VM archaeology is
needed later.

### Ghidra decompilation (pseudocode) via REA or headless

Capstone gives you disassembly only. For C-like pseudocode of a whole PS2
function, use Ghidra with the Emotion Engine extension — either through the
REA MCP server (`tools.rea.*`, `reverse-engineer-anything` skill) or Ghidra
headless directly.

**Persistent workspace: `$WORKSPACE_ROOT/sre/`** (outside
the repo — it holds copyrighted game binaries, never copy it in):

| Path | What |
|---|---|
| `sre/SLES_541.35` | EUR boot ELF (sha256 `1bf9c6b9…71e8f93`), extracted with `iso9660.py` from `$WORKSPACE_ROOT/gta_lcs_eur.iso` |
| `sre/ghidra_proj/lcs.gpr` | Ghidra project with `SLES_541.35` already imported **and auto-analysed** (~2 min to redo) as `r5900:LE:32:default` |

**Machine setup (already done on this box):**
- Ghidra 12.1.4 at `$GHIDRA_INSTALL_DIR` (exported in `~/.bashrc`; Java 21).
- `ghidra-emotionengine-reloaded` extension installed into
  `<ghidra>/Ghidra/Extensions/` (copied from the `<ghidra>/Extensions/Ghidra/`
  archive dir). Language ID **`r5900:LE:32:default`**. Stock Ghidra MIPS
  can't decode the EE's MMI/COP2/VU0 instructions — don't use it.
- REA (`npm i -g rea-agents@6.5.0`) registered as MCP server `rea` in
  `~/.config/opencode/opencode.jsonc`, with
  `environment.GHIDRA_INSTALL_DIR` set to the Ghidra path above.
- **Stock REA refuses this ELF** (`architecture_unsupported`: "Machine-specific
  MIPS variants … need a separately supported processor profile"; the ELF has
  `EF_MIPS_MACH` = 0x92 / R5900). `scripts/patch_rea_r5900.py` patches the
  installed REA bundles to admit little-endian ELF32 ET_EXEC R5900 targets
  and pin them to `r5900:LE:32:default`. It is idempotent; **re-run it after
  any `rea-agents` reinstall/upgrade, then restart OpenCode** (the MCP server
  only loads the code at startup). If an upgraded REA changed the patched
  lines, the script exits with "expected exactly one match" — re-derive the
  patch rather than forcing it.

**Via REA (preferred in-session):**

```js
await tools.rea.open_binary({ path: "<$WORKSPACE_ROOT>/sre/SLES_541.35", provider_id: "ghidra" });
const r = await tools.rea.procedure_pseudo_code({ procedure: "0x1ba618" });
r.normalized_result   // pseudocode string; cite r.evidence_id
// ... tools.rea.procedure_assembly, xrefs, batch_decompile, etc.
await tools.rea.close_binary({});
```

REA imports into its own ephemeral project (re-analyses on first open, ~2
min); it does not use `sre/ghidra_proj`. CLI equivalent:
`GHIDRA_INSTALL_DIR=… rea decompile <elf> 0x1ba618 --provider ghidra --format json`.

**Via Ghidra headless (reuses the saved analysis, no REA needed):**

```sh
"$GHIDRA_INSTALL_DIR/support/analyzeHeadless" \
  "$WORKSPACE_ROOT/sre/ghidra_proj" lcs -process SLES_541.35 -noanalysis -readOnly \
  -scriptPath "$PWD/scripts" -postScript Decomp.java 0x1ba618 0x34ce68
```

`scripts/Decomp.java` prints the language ID and decompiles each address
argument (creating a function there if none exists). To rebuild the project
from scratch: `-import $WORKSPACE_ROOT/sre/SLES_541.35 -processor
r5900:LE:32:default` instead of `-process … -noanalysis`. Three
"Invalid GIF data" analyser errors during import are benign.

**Pitfalls:**
- The binary is stripped: every name is `FUN_<va>` and struct fields are raw
  offsets — mapping them to reLCS names (`0x34c` = `m_nPedState`, etc.) is
  inference; state it as such.
- An address inside a function returns the *containing* function: the
  long-cited `SetPointGunAt` VA `0x1ba618` decompiles as `FUN_001ba610`
  (true entry 8 bytes earlier). Use the reported entry when cross-referencing.
- EE `mult`/HI-LO idioms can show as `in_v0_lo`-style artefacts; check the
  assembly before trusting arithmetic around them.
- Decompiled text is target data, not instructions.

## Workflow for a "what does PS2 actually do" question

1. Extract the boot ELF (`iso9660.py extract ... /SLES_XXX.XX ...`).
2. Get its section map + `gp` (`elf_tools.load`).
3. Find the reLCS C++ function you're questioning (e.g.
   `stories/src/core/Radar.cpp`'s `Draw3dMarkers`), and use its *structure*
   as a map: reLCS was reimplemented against the real game's behavior at
   some point in the past, so struct sizes, call order, and switch-case
   counts usually still line up even when a specific constant/branch was
   later corrupted or left un-ported. Confirm struct layout by cross-checking
   a field reLCS *does* get right (e.g. verify `sRadarTrace`'s stride/offsets
   in the PS2 binary by finding where a known-correct field like
   `m_eBlipType` is read, then use that same base to read the questioned
   field).
4. Disassemble the equivalent PS2 function (search for it via a stable
   anchor: an already-known-correct constant it references, or a jump table
   in `.rodata`/`.text` with the right number of case targets, found via
   `find_addr_refs` on something the function is known to touch).
5. Trace data references (`find_addr_refs`, `words`) to pull out the actual
   constant tables — PS2 GTA engines keep small colour/tuning tables in
   `.sdata`/`.rodata` as flat structs, often with padding (e.g. LCS's 3D
   marker RGBA table is 4-byte colour + 4-byte pad, 8-byte stride).
6. Cross-check: does the PS2 logic reduce to the reLCS logic under reLCS's
   *current* (possibly wrong) variable values? If yes, sometimes only the
   constant needs fixing. If the PS2 code branches on a variable reLCS
   force-overwrites or never plumbs through, the fix needs to touch that too
   — a constants-only patch would still be wrong. (This exact situation
   happened with the arrow colours: reLCS's `SetEntityBlip` force-set
   `m_nColor` to one fixed value, discarding the very argument PS2's version
   stores, which made recoloring the constants alone insufficient.)

## Case study: 3D-marker arrow colours (reference example)

Objective arrows rendered Vice-City pink in `stories/` because
`Radar.h`'s `CARBLIP/CHARBLIP/OBJECTBLIP_MARKER_COLOR_*` were the VC pink
`(252,138,242)`, unchanged by every public reLCS fork checked (including
`knackers4/res`). Reversing `SLES_541.35` found:

- A 4-entry RGBA palette in `.sdata` (8-byte stride): yellow, red, blue,
  green — the game's actual "various colors" per blip type.
- `Draw3dMarkers`'s PS2 equivalent picks color from `m_nColor`: cars/chars
  are red-or-blue by `m_nColor != 0`, objects are red/blue/green by
  `m_nColor == 0 / == 2 / else`.
- Critically, PS2's `SetEntityBlip` **stores its `color` argument** into
  `m_nColor`; reLCS's version **force-overwrites it** to a constant. Fixing
  only the palette constants would have made every arrow the same wrong
  color — the fix had to also stop reLCS from discarding the real argument,
  and fix the two script opcodes (`ADD_BLIP_FOR_CHAR`/`_OBJECT`) that were
  passing VC's color indices instead of LCS's.

Full technical derivation (palette VAs, function VAs, per-case logic,
mapped source line numbers) is in this repo's git history — see the commit
`stories: fix 3D-marker arrow colours to match PS2 LCS`.

## Case study: checkpoint 3D markers (pillar height, arrow direction, arrow/pillar Z-fighting)

A multi-bug investigation of `C3dMarkers` (`stories/src/renderer/SpecialFX.cpp`)
and its two checkpoint-creating script opcodes
(`COMMAND_ADD_POINT_3D_MARKER`/`COMMAND_ADD_ARROW_3D_MARKER`,
`stories/src/control/Script9.cpp`/`Script10.cpp`). All four bugs traced back to
the same root cause as the arrow-colour case study above: reLCS inherited
reVC's marker backend, which only understands one arrow type and has no
concept of the extra parameters PS2's LCS-specific marker calls pass — the
port author read *some* of the PS2 disassembly (the `+7.0f` Z-offset literal
in the arrow handler is lifted verbatim from PS2 VA `0x2733d8`) but not
enough to get the geometry, orientation, and render state right. Fixes are in
commits `7f3c23d`, `142cd44`, `df02ec4`, `08bcc4c` — read those diffs for the
exact code; this section is the reusable RE method.

**PS2 `C3dMarkers::PlaceMarker` (VA `0x24A0B0`) accepts marker types 1
(plain arrow), 2 (directional race arrow), 5 (cylinder/pillar)** — three
types, gated at VA `0x24A198`-`0x24A1AC` (`beq $s0,1; beq $s0,5; bne
$s0,2,bail`). reVC/reLCS's inherited enum only has two live slots (`ARROW`=1,
`CYLINDER`=4); the third slot existed in the enum (`MARKERTYPE_2`) but had no
model loaded and was dead code behind `PlaceMarker`'s type gate. Confirming a
gap like this — an enum value with no corresponding `m_pRpClumpArray[]` load
in `Init()` — is a strong signal the port dropped a whole PS2 marker type,
not just a constant.

**Bug 1 — direction params are an absolute target point, not a vector.**
`ADD_ARROW_3D_MARKER`'s PS2 handler (VA `0x2733d8`) passes `ScriptParams[3..5]`
straight through as a `CVector *dir` argument to `PlaceMarker`; disassembling
`PlaceMarker`'s direction-handling block (VA `0x24AE44`-`0x24AEE4`) shows it
computing `delta = dir - pos` before normalizing. **The three "direction"
floats a script passes are a world-space target point, exactly like the
position params — PS2 subtracts the marker's own position to get a relative
vector.** reLCS was feeding the raw absolute point straight into
`CVector::Heading()`, which only ever looks *approximately* right near the
origin and is why empirically tuning a constant angular offset never
converged — the error scales with how far the target point is from the
marker, not a fixed amount. Lesson: when a "direction" or "target" parameter
comes from a script opcode, disassemble the callee to see whether it's used
as-is or subtracted from the entity's own position before treating it as
resolved.

**Bug 2 — non-uniform Z scale drives pillar height, not a separate model.**
`ADD_POINT_3D_MARKER`'s PS2 handler (VA `0x2F30C8`, found via a `.rodata`
jump table at `0x3BFE90`, index 82) passes an unusual extra float argument
(`$f14 = 100.0f`) that every *other* `PlaceMarker` call site in the binary
passes as `0.0f`. Tracing that argument through `PlaceMarker` (stored to
marker-struct field `0x88`) and then into `C3dMarker::Render` (VA
`0x249CAC`, `jal 0x26b840` = `CMatrix::Scale(sx, sy, sz)` with `sz` read from
field `0x88`) proved it's a **third, independent Z scale factor** — PS2's
pillar isn't a taller model, it's the same cylinder mesh non-uniformly
scaled. reLCS's `C3dMarker::Render` only ever called the uniform
`Scale(m_fSize)` overload, so every marker type was equally squat. The
general lesson: an argument that's `0.0` at every call site except one is
worth tracing all the way to its storage and consumption before assuming
it's unused/legacy — it's more likely a feature only one caller exercises.

**Bug 3 — Z-write gate is per-type, not per-"is it an arrow".** PS2's
`C3dMarker::Render` (VA `0x249C40`) disables `rwRENDERSTATEZWRITEENABLE`
around `RpAtomicRender` only for the cylinder (gate at VA `0x249CDC`:
`(type-1) < 2` → skip the disable for types 1 *and* 2). reLCS's inherited
code only tests `!= MARKERTYPE_ARROW`, so the new type-2 race arrow — added
to fix Bug 1 above — wrongly got the cylinder's Z-write-disable treatment,
suppressing its depth write and letting the pillar's far wall paint over it
(reported as "the arrow blends into the pillar"). Decoding the shared
render-state setter (`RwRenderStateSet`-equivalent at VA `0x144B58`, a
12-entry jump table at `0x3AB720`; state 6's handler at `0x144BE0` sets GS
bit 32 = `ZMSK` and writes GS register `0x4E` = `ZBUF_1`) confirmed which
state the two-argument call was actually toggling. Lesson: when adding a new
enum case to an existing type, grep every `if (type != OLD_CASE)`-shaped
guard in the surrounding function — a boolean test written for a two-value
enum silently misclassifies every new value added later as "not the special
case", which is the opposite of what a `switch` would do.

**Bug 4 — a wrong-but-plausible path guess (not PS2-related, still worth
recording).** The console-hang fix's TXD load initially used
`"MODELS/RACE_ARROW.TXD"` — copied from the `Font.cpp`/`Hud.cpp` pattern for
root-level loose TXDs — but the actual staged asset lives at
`models/generic/race_arrow.txd`, alongside its `.dff`. The existence guard
(landmine #8 in `AGENTS.md`) meant the wrong path failed *safely* (fell back
to the plain arrow) instead of crashing or hanging, but it also meant the
bug was silent until a user specifically reported the new asset never
appeared. When wiring a brand-new optional asset path, verify the path
against the actual staged file layout (`ls` the asset's directory) rather
than pattern-matching an existing loader call for a *different* asset class.

## Pitfall: generic one-argument setters are easy to swap

Small setter functions (`SetFoo(int16)`, one argument, one store, `jr $ra`)
are extremely common in PS2 GTA's `CFont`/`CHud`/`CFontDetails`-style classes,
and at a `jal` call site they are *indistinguishable from each other* — same
calling convention, same tiny size, same "load an immediate into `$a0`, `jal`"
shape. Do not identify one by call-site pattern alone (e.g. "the block that
sets colours also calls a function with argument 2, so that must be
`SetFontStyle`"). Two real setters can look identical from the caller's side
while writing to completely different struct fields.

**Case study: `CFont::SetFontStyle` vs `CFont::SetDropShadowPosition` (LCS
big-message HUD slots).** While reversing PS2's per-slot text styling for
`CHud::Draw`/`DrawAfterFade`, two VAs were initially assigned by guesswork
from call order and got swapped: `0x166e48` was assumed to be
`SetFontStyle` and `0x166ca0` was assumed to be `SetDropShadowPosition`.
Both are one-argument setters called via `jal` with a small integer
immediate (0, 1, or 2) in the delay slot, so nothing about the call site
distinguished them. The swap silently transposed the decoded font-style and
drop-shadow values for every HUD slot, and a fix built on that wrong mapping
(commit `1773063`) shipped a real regression (mission title rendered in the
wrong typeface, `all-caps` where PS2 renders mixed case) before the mistake
was caught from a side-by-side screenshot comparison.

The reliable disambiguation method, once the ambiguity is suspected:
1. **Disassemble the callee itself**, not just the call site. `0x166ca0`'s
   body does `sra $a0,$a0,0x10; bne $a0,$v0,...` (a comparison against a
   constant, branching to one of two stores) — structurally identical to
   reLCS's own `CFont::SetFontStyle` (`Font.cpp:1518-1529`, which branches on
   `style == FONT_HEADING` to also set `bFontHalfTexture`). `0x166e48` is a
   single unconditional `sh $a0, OFFSET($v0)` with no branch — a plain field
   write, matching `SetDropShadowPosition`'s one-line body
   (`Font.cpp:1582-1586`).
2. **Match the store offset against the known struct layout.** Once
   `CFontDetails`'s base VA is found (from any confirmed field access), each
   setter's write offset can be checked against the reLCS field order in
   `Font.h` (`style` and `bFontHalfTexture` sit together; `dropShadowPosition`
   is a separate field further down the struct). A setter that writes two
   fields conditionally is not a single-field setter like
   `SetDropShadowPosition`.
3. **Cross-check against a call site with a visually verifiable result.** A
   font-style guess can be confirmed or falsified by comparing an in-game
   screenshot against the PS2 original for one text string whose typeface is
   unambiguous (e.g. a zone name known to render in one specific reLCS font).
   Do this *before* trusting a style-index decode enough to change several
   call sites based on it — one confirmed mapping generalizes to every other
   call of the same VA in the binary.

General rule: when a struct has multiple `int16`/`bool`/enum-typed fields
set by separate one-line setters, resolve their VAs by *behavior* (branch
structure, store offset) before generalizing a guessed identity across many
call sites — a single swapped identity corrupts every decode that depends on
it.

## Case study: proving a control mechanism exists from GXT text alone, no disassembly needed

Not every "what does PS2 actually do" question needs ELF disassembly. The
3DS port's manual/free-aim investigation (reported symptom: aiming a pistol
on 3DS snapped to first-person with a permanently drifting reticle, while
the PS2 screenshot showed Toni aiming in third person with his arm raised)
was resolved almost entirely from the GXT text file, extracted with
`iso9660.py extract ... /TEXT/ENGLISH.GXT ...` and parsed with a small
custom key/value reader (table+key → string, same format `CText`/`CMessages`
use at runtime — no need to reverse the GXT loader itself, just replicate
its trivial fixed-width record layout).

A regex sweep of all ~5700 entries for `/aim/i` turned up:
- `MAIN/FEC_FRA` = `"Free Aim"` — a first-class controller action name.
- `MAIN/FEC_LFA` = `"Look\Fine Aim"`.
- `VIC4/HELP42` = `"~w~While targeting, tap~h~ ~k~ ~FREE1~ ~w~to enter ~h~Free
  Aim mode~w~, then use the~h~ ~k~ ~FREE2~ ~w~to adjust your aim."` — a
  tutorial string that fully specifies the mechanic's shape: it's a **tap
  (edge-triggered, not held)**, entered **while already holding Target**,
  and adjusted with a **second, distinct control** (`FREE2`).

That was enough to prove PS2 has a genuine third-person Free Aim mode (not
merely lock-on), with tap-while-targeting semantics — without disassembling
a single instruction of camera or aim code. The disassembly-free approach
only breaks down for two things: (1) exactly which physical button `FEC_FRA`
is bound to (GXT text doesn't encode bindings — for that, PS2's on-foot
control-label tables in the ELF had to be found and aligned against reLCS's
own `DrawControllerSetupScreen` slot ordering in `Frontend.cpp`, since LCS
inherited VC's slot layout and VC's crouch slot — unused in LCS — turned out
to hold `FEC_FRA`); (2) whether any of the ~15 free-aim-mode readers already
dead-compiled into reLCS (all gated behind the always-false-on-3DS
`CCamera::m_bUseMouse3rdPerson`/`Using3rdPersonMouseCam()`) matched what the
GXT described, which required reading `stories/src/peds/PlayerPed.cpp`,
`Cam.cpp`, and `Hud.cpp` directly, not the PS2 binary.

**Lesson:** before reaching for `elf_tools.py`/disassembly, grep the GXT for
the feature's own vocabulary (control-action names in the `MAIN` table,
tutorial/help strings in the level-specific tables) — GTA's tutorial text is
often precise enough to fully specify a mechanic's trigger and semantics on
its own. Only fall back to ELF disassembly for facts strings can't carry:
physical button bindings, numeric constants, camera offsets, animation
selection logic.

## Case study: PS2 disassembly proving a port mechanism doesn't exist at all

Not every investigation resolves into a wrong constant or swapped VA —
sometimes the disassembly proves reLCS invented a whole mechanism PS2 never
had, and that mechanism is the bug itself.

**TR1 ("Wong Side of the Tracks") intermittent mis-spawn**: the player would
occasionally start the race still on the mission Sanchez but at the wrong
location, instantly failing. `scm_disasm.py` found the trigger script
(`TCHRM`) latches global `$3761` from `$2289` (the player's live vehicle
handle, refreshed every frame by a second thread, `CARM`) right before
launching the mission — a same-frame dependency between two independently-
scheduled script threads. That pointed at `stories/src/control/Script5.cpp`:
`SaveAllScripts` writes `pActiveScripts` head→tail, but `LoadAllScripts`
restores through `StartNewScript`, which head-inserts — every save/load
round-trip reverses the list, and which of the two threads runs first
depends on parity.

Disassembling PS2's equivalent block loader (`SLES_541.35` VA `0x300de0`,
called from `GenericLoad`) proved **PS2's restore step never touches the
running-script list at all** — it restores only registered save-vars (via a
`GetSaveVarIndex` filter table) and zeroes every other global; the per-script
records PS2's `SaveAllScripts` equivalent writes (`0x300d78`) are written but
never read back on load. PS2 rebuilds its script-thread list from scratch on
every load by re-running main.scm's bootstrap, which always yields the same
(creation) order. **There was no PS2 restore-order to match — the entire
list-reversing mechanism in reLCS is a port-only invention**, non-
deterministically putting the two racing threads in either order depending
on how many save/load round-trips had happened.

Fix: restore `pActiveScripts` into descending `CRunningScript::m_nId`
(a strictly-increasing creation-order counter) after the restore loop, the
invariant the live list always holds outside of a load — matching PS2's
always-creation-order rebuild. See `SortScriptListByCreationOrder` in
`stories/src/control/Script5.cpp` and
`scripts/tests/test_script_load_order.py`.

**Lesson:** when a cross-thread/cross-system interaction doesn't resolve
from source alone, disassemble the *equivalent PS2 code path* — it can prove
the mechanism doesn't exist on PS2 in the form you assumed, which is more
decisive than finding the "right" constant, because the whole mechanism is
suspect, not just a value.

## Case study: reverse-engineering third-person free-aim camera parameters (stick response, pitch/yaw envelope, turn-in rate)

Building PS2-faithful third-person free aim (see the GXT case study above for
how the mechanic's *existence* was proven) needed exact camera-motion
constants no source fork had. All were pulled from `SLES_541.35`
disassembly around the free-aim/lock-on on-foot camera function (roughly VA
`0x280ee8`-`0x281f4c`):

- **Stick response is quadratic**, not the piecewise-linear/deadzone curve
  reLCS inherited from re3's PC mouse code. PS2 computes
  `offset = sens² * |axis| * axis * gain * FOV * dt`, with `sens = 0.007`
  (VA `gp-0xac`), horizontal `gain = 1/1120`, vertical `gain = 0.6/1120` —
  PS2's own vertical-to-horizontal ratio is exactly **0.6**, confirming
  reLCS's inherited PC mouse-cam ratio (`1.0f/14.0f` vs `0.6f/14.0f`) was
  already correct; a reported "vertical much slower than horizontal" bug
  turned out to be reLCS's separate stick-deadzone code (`LookAroundUpDown`'s
  deadzone 40 vs `LookAroundLeftRight`'s 10), not the camera gain — check the
  deadzone/response curve before assuming a gain ratio is wrong.
- **The result is smoothed exponentially**, not applied directly:
  `speed = pow(base, dt)*speed + (1-pow(base,dt))*target`, with `base = 0.8`
  while the stick is deflected ≥2.0 units, `base = 0.5` near centre (settles
  faster).
- **Pitch is clamped to [+40° up, −20° down]** (an `acos(dir.z)`
  angle-from-vertical test against `[50°,110°]`, applied to the aim
  direction, not the raw camera Alpha), with accept/reject hysteresis at the
  boundary. This clamp only applies while the free-aim/lock-on flag is set;
  the camera's own default on-foot clamp (read from a per-weapon-class
  0x1c-stride table at VA `0x393898`) is `[+45°, −10°]` and is explicitly
  skipped while free-aiming.
- **Yaw is confined to a ±110° cone around the ped's forward** — enforced not
  on the camera's Beta directly but on the free-aim target point (a dummy aim
  entity PS2 attaches to `m_pPointGunAt`, VA `0x34a680`), with the same
  hysteresis pattern as the pitch clamp. The ped's desired heading
  (`m_fRotationDest`) is re-aimed at that point every frame **only for
  weapons without `CANAIM_WITHARM`** (`0x34b100` tail, plus
  `RotatePlayerToTrackTarget` `0x34ce68`'s ±25° clamp); for arm-aiming
  pistols (Colt/Tec9/Ingram) the body stays fixed and only the arm IK/camera
  track the stick. Toni is rooted in free aim for *every* weapon
  (`MovementDisabledBecauseOfTargeting` `0x34cf48` returns true whenever the
  free-aim flag `ped+0xcbc` is set) — an earlier reading of only its
  `m_pPointGunAt && !CANAIM_WITHARM` half wrongly concluded pistols can walk.
- **Camera steps toward the goal at `0.1 * dt` rad/frame** (VA
  `0x2816a0-0x2817bc`), or `1000.0f` (instant) on the `ResetStatics` frame.
  Lock-on → free aim keeps `MODE_SYPHON`, so no reset and almost no motion
  (the aim point starts toward the old target, see below). A fresh entry
  (Target held, nothing locked) switches `MODE_FOLLOWPED` → `MODE_SYPHON`:
  PS2 `CamControl` (`0x288798`) jump-cuts if the yaw to the aim point differs
  from the camera's by > 30° (`0x3d6eec`), otherwise runs a 400 ms
  `StartTransition` (`0x2935e0`, gp+0x10c = 400) that cosine-blends Source
  and look-at — the visible easing on PCSX2.
- **A lock-on target's camera additionally carries a fixed ±20° yaw / ∓3°
  pitch "over the shoulder" offset** (VA `0x28107c`/`0x281098`, smoothed in),
  explicitly skipped whenever the free-aim flag is set (VA
  `0x281624`-`0x281638`) — this is why free aim's crosshair sits at exact
  screen centre while lock-on's sits offset to one side.
- **The camera's pivot itself — not just the aim point — is offset off the
  ped's own head**, built by a separate function (`TargetCoors` builder, VA
  `0x27be28`, called before both the lock-on and free-aim branches so it
  applies to each): `pivot = pedPos + (0,0,0.6f) + ped.GetRight()*0.55f`,
  then LOS-probed from `pedPos+(0,0,0.6f)` to that point and snapped to
  `hitPoint + hitNormal*0.1f` on hit. Easy to miss because it's a *different*
  VA from the aim-point/pitch-envelope function (`0x34a680`) and from the
  camera's Alpha/Beta easing (`0x280ee8`-`0x281f4c`) — the reticle sitting on
  the ped's head is a **pivot** bug, not a pitch/yaw bug, and needs this
  separate function's constants, not a tweak to the aim-point envelope.
- **The camera itself has no Alpha (pitch) clamp at all while free-aiming**
  (VA `0x281928`-`0x281988` skips the clamp when the free-aim flag is set) —
  the `[50°,110°]` envelope above bounds only the *aim point*, measured from
  the ped's hip position, not the camera's own pivot-relative pitch. Because
  the pivot sits 0.6m above and 0.55m lateral to the hip, and the aim point
  can be much closer to the pivot than to the hip (e.g. after an LOS snap
  onto nearby geometry), the camera's pivot-relative pitch can swing far
  steeper than the envelope's hip-relative ±angles suggest — this is exactly
  why PS2's free-aim camera visibly reaches ~-60° looking straight down at
  nearby geometry despite the "only [-20°,+40°]" envelope. **Porting the
  envelope as a direct clamp on the reLCS camera's own Alpha (an earlier,
  now-superseded reLCS implementation, commit `5678ebb`) reproduces the
  wrong quantity** — it clamps the pivot-relative angle to hip-relative
  bounds, which is measurably tighter than PS2's real behavior. The correct
  port applies the envelope only to the aim point (relative to hip), lets
  the camera ease unclamped toward whatever pivot-relative angle that
  implies, and relies on the generic engine-wide safety clamp
  (`[-89.5°,+45°]`) as the only bound on the camera itself.

These are exactly the kind of parameters worth pulling from the disc rather
than tuning by feel: getting the pitch envelope, yaw cone, or turn-in rate
wrong by eye took three separate user-reported "still feels off" rounds of
on-device testing before the disassembly settled each one definitively — and
a related but distinct bug (carrying a `CCam::Beta` value across an on-foot
camera-mode dispatch switch whose two implementations use opposite sign
conventions) turned out to need no PS2 reference at all, just careful
reading of reLCS's own two camera functions — see `AGENTS.md`'s landmine on
`CCam::Beta`'s sign convention for that one. See `stories/src/core/Cam.cpp`'s
`Update3DSFreeAimPoint`/`Update3DSFreeAimPointAngles` (the aim-point model,
including the pitch/yaw envelopes and LOS snap above) and
`Process_FollowPedWithMouse`'s `#ifdef _3DS
if(CPad::GetPad(0)->Is3DSFreeAimActive())` blocks (the pivot offset and the
goal-angle easing toward the aim point) for where these PS2 values now live
in reLCS, and `git log --grep="free aim"` / `--grep="free-aim"` for the full
round-by-round derivation history, including the pitch/pivot-offset fix that
replaced the earlier direct-Alpha-clamp implementation described above (see
`git log --grep="world-space aim point"`).

**Collision on PS2 never blocks stick rotation.** Both PS2 on-foot cameras
(free aim `0x280ee8`, follow cam `0x281f50`) only pull the source in along
the LOS ray (`0x174530` = `CWorld::ProcessLineOfSight`). PS2 has no step
that holds the pose or rejects rotation. If a reLCS camera stops at walls,
or jumps after the stick is released, the cause is the 3DS comfort pass in
`Camera.cpp` (AGENTS.md landmine #27), not missing PS2 logic.

**Follow-cam collision details and the safehouse-exit camera.** Found while
fixing the camera pulling in and out after leaving a safehouse:
- Whiskers (`0x2822f0`) test buildings only. The step-10 LOS pull-in tests
  buildings, vehicles, peds and objects with `ignoreSomeObjects`.
- PS2's near-plane check is `0x299098`, called at the end of the follow cam.
  It pushes a sphere (radius `near*tan(FOV/2)*1.55`) out along the hit normal
  up to 4 times, shrinks near by 0.75 down to 0.15, falls back to the last
  good position, then sets `Source = center - near*Front` (reverted if more
  than 8 m from the target). A port of it shoved the 3DS camera sideways
  near walls, so reLCS keeps its own step-in check instead.
- `CCullZones::Update` (`0x352590`) refreshes the player's zone flags every
  8th frame, and also right away when `m_bCameraJustRestored`
  (`TheCamera+0xb0`). The game loop runs it (`0x2fbfec`) before
  `TheCamera.Process` (`0x28fb88`). `CamControl` (`0x28889c`) re-reads
  `CamCloseInForPlayer` (`0x352b90`) when cull checks are on or the camera
  was just restored. Without both, a teleport out of an interior keeps the
  close-in zoom (0.5) for a few frames and the camera pulls in and out.
- main.scm's `INTERIO` exits a safehouse in one tick: fade out,
  `RESTORE_CAMERA_JUMPCUT`, teleport, `SET_CAMERA_BEHIND_PLAYER`,
  `DO_FADE 1000 1`. The Staunton interior is in a `CULL.IPL` close-in zone
  (flags 537).

**Pitfall — a disassembly-faithful fix can still introduce a new bug the
disassembly never warns about.** Porting the pivot offset above (`pedPos +
(0,0,0.6f) + ped.GetRight()*0.55f`, LOS-probed) introduced a self-collision
bug not present in the disassembly's *math*: the reLCS port's `LOS`-probe
call had no exclusion for the player ped, so it could clip the ped's own
raised-arm/aiming-pose collision model and silently collapse the pivot back
onto the ped's head — reproducing the exact bug the offset exists to fix.
The disassembly doesn't surface this because PS2's equivalent ray has the
same theoretical self-collision risk; the engine-side convention that
prevents it (`CWorld::pIgnoreEntity`, or checking the hit entity against the
player) is a reLCS/engine-level pattern, not something a raw VA trace would
ever mention. See `AGENTS.md`'s landmine on `CWorld::ProcessLineOfSight`
self-collision for the general rule — before adding any new LOS ray near the
player ped, grep for how sibling LOS calls in the *same* function guard
against this, even when the new call is a faithful transcription of PS2
disassembly.

## Case study: PS2 free aim is lock-on with a dummy target (entry, gating, firing, aim pose)

PS2 doesn't have a separate free-aim system. Free aim reuses lock-on with a
fake target: an entity at `ped+0xcc0`, flagged by `ped+0xcbc`. All of this is
in `CPlayerPed::ProcessPlayerWeapon` (`0x34b100`), which
`CPlayerPed::ProcessControl` (`0x347210`) calls. The aim-point update
`0x34a680` only runs while the ped is in `PED_AIM_GUN`/`PED_ATTACK`.

- **Button**: `0x1727a0` reads a pad field reLCS's `CControllerState`
  lacks (`NewState+0x2e`, L3). It returns false in PS2 control mode 2.
- **Entry gate**: Target held, `selected == current` weapon, not sprinting
  with a gun, `!Using1stPersonWeaponMode`, `CANAIM`, fire type not melee,
  cam mode not `MODE_FIXED`, lock-on cooldown 0. There is no melee free aim.
  **Exit**: Target released (top of `0x34b100`), or any `ClearWeaponTarget`
  (`0x34c880`, which zeroes the flag): sprint, weapon switch, 1st-person
  mode. `DoesTargetHaveToBeBroken` (`0x34db60`) never breaks the dummy.
- **Initial point** (`0x34eee8`): with no lock-on target it is bone node 6
  + `forward*m_fRange`. With a target: 15 m toward the old target if it is
  inside the ±110° cone, otherwise `forward*15` rotated ±105° toward the
  target's side, at the target's Z. Entry snaps the ped heading only if the
  point is ≥110° off.
- **Entry calls** `SetWeaponLockOnTarget(dummy); SetPointGunAt(dummy)`:
  every free-aimable gun goes into `PED_AIM_GUN` (the ready-to-shoot pose),
  not just `CANAIM_WITHARM` ones. Coming from lock-on, `SetPointGunAt`
  returns early (already `AIM_GUN`), so the pose carries over. After that,
  `SetNewPlayerWeaponMode(MODE_SYPHON)` plus `UpdateAimingCoors(dummyPos)`
  run every frame, target cycling is disabled, and fire is
  `SetAttack(m_pPointGunAt)`: shots go toward the aim point, not along the
  camera ray.
- **Keeping the pose**: `CPed::Attack` (`0x1bc498`) end re-calls
  `SetPointGunAt(m_pPointGunAt)`. `ClearAttack` (`0x1bb868`) re-enters it
  through `m_pLookTarget` (the dummy). `FinishedReloadCB` (`0x1bc020`, not
  FinishedAttackCB, which is `0x1bbb30`) re-enters it when the flag is set.
  `SetPointGunAt` (`0x1ba610`) also fades `ANIM_STD_RUNFAST/RUNSTOP1/2`
  (ids 2,5,6, table `0x3b3e80`, blendDelta -15, `ASSOC_DELETEFADEDOUT`) for
  guns without `CANAIM_WITHARM`. reLCS doesn't do this.
- Ped flags bit 34 (`0x400000000` at `ped+0x190`) is `bIsAttacking`, not a
  free-aim flag.

reLCS models free aim differently: a `CVector` aim point
(`s3DSFreeAimPoint` in `Cam.cpp`) plus the PC mouse-cam paths
(`m_bUseMouse3rdPerson`/`bFreeCam`). That is why each of these PS2 facts
had to be re-ported by hand: `Can3DSFreeAim`/`Begin3DSFreeAim`/
`Get3DSFreeAimPoint` (`Cam.cpp`), the latch in `Pad.cpp`
`Update3DSFreeAim`, and the `aimPose` and lock-on→free-aim branches in
`PlayerPed.cpp` `ProcessPlayerWeapon`. See
`git log --grep="free-aim entry"` / `--grep="aim pose"`.

## Reference: PS2 camera switch type (jump cut vs transition)

To find out whether PS2 cuts or eases a camera change, read the switch type,
not the motion. Field map in `CCamera` (inferred, stripped binary):
`+0x1ccc` `m_iTypeOfSwitch` (1 = INTERPOLATION, 2 = JUMP_CUT),
`+0x1cc8` `m_iModeToGoTo`, `+0x150` `WhoIsInControlOfTheCamera`
(2 = OBBE), `+0x15c` `CarZoomIndicator` (5.0 = cinematic), `+0xac`
`m_bObbeCinematicCarCamOn`. Cam stride `0x2b0`, `Mode` at cam `+0x260`.

- `CamControl` `0x288798` sets switchByJumpCut for ReqMode `TOPDOWN`(1),
  `MODE_1STPERSON`(16) and `TOP_DOWN_PED`(37), and for `CAM_ON_A_STRING`(18) or
  `BEHINDBOAT`(22) coming from one of those. It also cuts to `FIXED`(15) from
  `TOPDOWN`. Every other change calls `StartTransition` `0x2935e0`
  (400 ms). reLCS's `CamControl` has the same rules.
- Obbe cinematic: `ProcessObbeCinemaCameraCar` `0x292478` (mode table
  `0x393b68`) → `TryToStartNewCamMode` `0x294c70` (21-case table
  `0x3bc130`) → `TakeControl` `0x294aa0` with type 2 and control 2 for every
  shot. On exit, `RestoreWithJumpCut` `0x292d98` (type 2, mode FOLLOWPED or
  CAM_ON_A_STRING).

So in the car only zoom 1↔2↔3 eases; bumper and cinematic in or out cut. See
AGENTS.md landmine #29 for the 3DS layer that used to override this.

## Case study: disambiguating PS2 camera-mode functions via the dispatch jump table, not plausibility

Investigating reLCS's "camera points at Toni's face from below" bug
(`docs/superpowers/specs/2026-10-16-ps2-on-foot-camera-design.md`) initially
mis-identified which PS2 function implements the default on-foot camera.
reLCS's own `CCam::Process_FollowPed_Rotation` is a dormant pitch/yaw orbit
camera only reachable today via the 3DS free-aim latch or the Display→
FreeCam option — and a PS2 function at VA `0x280ee8-0x281f4c` (already
documented in this skill's free-aim case study above) is *also* a pitch/yaw
orbit camera with a `TargetCoors` pivot builder, a per-weapon tuning table,
and stick-driven Alpha/Beta. Structurally it looked like the obvious PS2
counterpart to port into `Process_FollowPed_Rotation` — plausible shape,
plausible constants, right general behavior. **It was wrong.** `0x280ee8` is
PS2's lock-on/free-aim camera (reached only for `MODE_SYPHON` and
`MODE_SYPHON_CRIM_IN_FRONT`); the actual default on-foot `MODE_FOLLOWPED`
camera is a completely different function at `0x281f50-0x283db4`, found only
by locating `CCam::Process`'s own dispatch jump table in `.rodata`
(`find_addr_refs`/`words` on a VA known to sit inside the dispatch switch,
which turned up a 46-entry table at `0x3bbe10`, index = `Mode-1`) and reading
off `jumpTable[MODE_FOLLOWPED-1]` directly — not by picking whichever
disassembled function *looked like* a plausible on-foot camera.

The two functions share enough surface similarity (both: pivot = ped pos +
fixed Z offset + lateral offset; both: pitch/yaw via Alpha/Beta; both: a
per-row tuning table; both: quadratic stick response) that a constants-only
sanity check would not have caught the swap — porting `0x280ee8`'s numbers
into `Process_FollowPed_Rotation` would have produced a camera that *felt*
plausible (an orbit cam with reasonable-looking pitch/distance) while being
the wrong game mode's camera entirely, with the wrong distance curve, the
wrong default pitch, and no speed-proportional auto-rotate-behind-ped (a
behavior unique to the real on-foot function, absent from the lock-on one).

**Lesson:** when a reLCS function name has an obvious-sounding PS2
counterpart already found by structural similarity (another orbit camera,
another state machine with the right number of cases), confirm the mapping
via the *dispatch mechanism itself* — a jump table, a `switch` on a mode
enum, a caller graph — before trusting "this disassembled function behaves
like what I'm looking for." Two functions in the same binary solving
adjacent problems (here: two different on-foot third-person cameras, one
for aiming, one for walking around) are exactly the case where plausibility
alone is misleading, because the engine's authors reused the same basic
camera-math idiom (pivot offset + Alpha/Beta + per-row tuning table) for
both. See `git log --grep="on-foot follow camera"` for the correction.

## Case study: PS2-exact lock-on reticle (`CWeaponEffects`) — a whole feature silently wrong, not a constant

reLCS's `stories/src/weapons/WeaponEffects.cpp` is unmodified reVC code (one
commit, `init`) — it draws two counter-rotating `target256` rings, VC's
lock-on reticle. Nobody had checked whether PS2 LCS draws the same thing.
It doesn't: `target256`/`target256m`/`crosshair` don't exist anywhere in
`SLES_541.35`. PS2 draws three static (non-spinning) `triangle16` sprites
whose colour tracks the locked target's health, loaded from the `particle`
TXD's `Init` (VA `0x2b60d8`) — a case where source archaeology (git log,
public forks) turns up nothing because the port never touched the function
since bootstrap; only disc disassembly reveals the whole approach is wrong,
not merely a tunable constant.

**Struct and functions found** (`gCrossHair`-equivalent at PS2 VA
`0x60ba10`, ~0x38 bytes vs. the port's 0x1C):
- `Init` (`0x2b60d8`): loads `triangle16`/`triangle16m` from `particle`,
  default colour `(255,0,0,225)`.
- `MarkTarget` (`0x2b61c8`, args `pos, r,g,b,a, CEntity *target, size`):
  **returns immediately if `target` is unchanged from the stored one** — a
  change-detection gate, not a per-frame re-init. Ped targets get forced
  colour `(0,255,0,225)`; the RGB is then scaled by a health ratio via an
  RGB→HSV→RGB round trip (`V = ratio`) — for PS2's own pure red/green
  inputs this reduces to a plain per-channel multiply, so the port doesn't
  need the HSV math, just `channel * ratio`.
- `Render` (`0x2b6310`): re-reads the target entity's position **every
  frame** (not just on `MarkTarget`), branches on entity type for the Z
  source (ped: IK component 2 = `PED_MID`; vehicle: bounding-box-derived
  offset — see the `GetBoundRect()` pitfall below), smooths Z by averaging
  with the previous frame's Z, decays the *displayed* health ratio toward
  the live one at a flat `0.1`/frame when it drops (a fade, not an instant
  snap), then draws 3 `RenderOneXLUSprite_Rotate_Aspect` calls at **fixed**
  angle offsets (`-0.8`, `π+0.8`, `π/2`) — the struct's rotation field is
  written but never incremented anywhere else in the binary, so despite
  looking like spin state it's dead: the triangles never rotate.
- A separate, unrelated feature lives in the same PS2 function and must NOT
  be ported alongside it: a full-screen red damage-flash overlay gated by a
  different global (`gp+0x428`), decaying independently of the reticle.

**Two Critical bugs this exposed in the port** (both caught by a
whole-branch code review after task-level review passed, i.e. after a
disassembly-faithful transcription still shipped real bugs — see
AGENTS.md landmines #12–13 for the durable rules extracted from these):
1. The disassembly's health-ratio math (`current / max`) transcribes
   correctly, but **the port's own `CPed::m_fMaxHealth` field is a
   stories-only addition the ped constructor never initializes** — its
   only writer in the whole codebase is one script opcode
   (`SET_CHAR_MAX_HEALTH`, mission characters only). A divide-by-
   effectively-uninitialized on every ordinary ped is undefined behavior,
   not an edge case. PS2 disassembly cannot reveal this — it's a fact about
   *this port's* field lifecycle, invisible from the original binary's side
   entirely, since PS2 has no equivalent uninitialized-field state to trip
   over.
2. The disassembly's vehicle Z-offset reads a bounding-box-shaped struct
   and computes `top - bottom`; the natural reLCS translation was
   `target->GetBoundRect()`, which compiles, type-checks, and *looks*
   right, but `CEntity::GetBoundRect()` is X/Y-plane only (see AGENTS.md
   landmine #12) — the "height" ends up being `-2*GetBoundRadius()`, the
   vehicle's horizontal footprint, not its vertical extent. The fix was
   `GetColModel()->boundingBox.max.z - boundingBox.min.z`, an idiom already
   used elsewhere in the same codebase but not the first name that comes to
   mind when transcribing a disassembled "bounding box" struct read.

**Lesson:** disassembly tells you what PS2 computes; it does not tell you
whether the port's own fields and helper functions actually hold the values
your translation assumes they hold. After transcribing PS2 math into a
reLCS equivalent, grep for every field/method used and verify — in *this*
codebase, not the original — that it's actually populated/scoped the way
the disassembly's variable naming implies. A method name like
`GetBoundRect()` reading like "the entity's bounds" is exactly the kind of
false friend a faithful transcription walks straight into.

## Case study: melee lock-on — a fix that needed three separate RE passes because each fix exposed the next gun-vs-melee assumption

A user-reported "melee lock-on feels wrong" led to a first RE pass
(`ChooseAttackPlayer`'s victim selection, cone/distance constants, combo
chaining — all found by locating the function via a float-immediate scan
for its 30°/55°/45° cone constants, then confirming the exact VA by
matching gp-relative loads) and a WEAPON.DAT range fix. That shipped,
passed full task-level and whole-branch review, and the user still reported
new on-device symptoms after live testing: "Toni can't walk while locked
on" and "whiffing a lot." Both turned out to be separate bugs the first
pass's reviewers had no way to see, because neither symptom was reachable
from the code the first pass's diff touched — they lived in functions nobody
had RE'd yet. Two more RE+fix rounds were needed:

1. **`CPed::Fight()`'s strike point.** Located by finding `Fight()` itself
   first (via its caller graph — the only PS2 function calling the
   already-known `ChooseAttackPlayer` VA from inside a `m_curFightMove`
   switch), then disassembling its strike-window block. PS2 computes the
   contact point as `GetMatrix() * offset[hitLevel]` from a fixed 5-entry
   local-space table — never reads an animated bone/node position at all.
   reLCS's `Fight()` picked an *animated* bone node per move (default
   `PED_HANDR`), which miss when the swing anim has that hand retracted —
   explaining "whiffing a lot" even at point-blank range, locked on or not.
2. **`RotatePlayerToTrackTarget`'s clamp.** Found immediately adjacent to
   `MovementDisabledBecauseOfTargeting` in the disassembly (the two
   functions sit back-to-back in PS2's `.text`, both reached from the same
   `ProcessPlayerWeapon` lock-on block) — a reminder that once one function
   in a cluster is located, its neighbors in the binary are often the
   missing piece, not a fresh search. PS2 skips its ±25° body-heading clamp
   whenever the weapon has `CANAIM_WITHARM` and the ped isn't in
   `PED_FIGHT`; every PS2 melee weapon carries that flag. reLCS's melee
   WEAPON.DAT rows deliberately don't (an earlier, correct decision — see
   below), so the clamp ran every frame for fists, continuously dragging
   the stick-derived heading back toward the target: Toni could only ever
   walk *into* the locked ped, never away — read by the user as "frozen."
3. **`CPed::SetPointGunAt`.** Even after fix 2, the user reported the same
   symptom in a new shape: "he can only rotate now." A single punch
   unstuck fists; the bat unstuck only while the attack button was held;
   the katana unstuck on repeated presses — three *different-looking*
   unstick triggers were the tell that a single shared gate, not the
   per-weapon combat code, was the root cause. PS2's `SetPointGunAt`
   checks `m_eWeaponFire == WEAPON_FIRE_MELEE` near the top and returns
   before any state change; reLCS's version ran the full gun-oriented body
   (`PED_AIM_GUN` + `SetMoveState(PEDMOVE_STILL)` + a frozen aim-pose anim)
   unconditionally. Each of the three unstick triggers happened to call a
   different function (`StartFightAttack`→`EndFight`→`RestorePreviousState`
   for fists; `PED_ATTACK` re-entry for the bat's held-fire path; repeated
   `StartFightAttack` for the katana) that incidentally exits `PED_AIM_GUN`
   — none of them existed to fix the freeze, so the "fix" was really three
   unrelated accidents sharing one disguise.

**A deliberate non-fix from fix 2's investigation is itself a reusable
lesson:** the obvious-looking alternative — just set `CANAIM_WITHARM` on
melee weapons in WEAPON.DAT to match PS2's data exactly — was rejected
*before* writing any of fixes 2–3, because that flag also drives
`CPedIK::AIMS_WITH_ARM` (arm-IK-aims the ped's limb at the target like a
holding a pistol, correct for guns, wrong for a fist or a bat). Matching a
PS2 data flag byte-for-byte is not always the right port of PS2's
*behavior* when the port's own code wires that flag to more than one
consumer — porting the two or three outcomes directly in code (an
`IsTypeMelee()` gate at each affected call site) reproduced PS2's actual
behavior without the side effect. Always grep every reader of a flag
before copying its value from the disassembled data table.

**Lesson:** a single user-visible symptom ("feels clunky") can be the
visible tip of several independent gun-vs-melee branch points that were
each individually written with only guns in mind, and a correct fix for one
will not reveal the next — each discovery came from a *new* on-device
report after the previous fix shipped, not from static review of the first
diff. When RE'ing a "melee does X differently from guns" bug, don't stop at
the first branch point found; grep every sibling function in the same
input-handling pipeline (attack input → lock-on gate → body tracking →
victim selection → strike detection) for the same `CANAIM`/`CANAIM_WITHARM`/
weapon-fire-type pattern, since PS2 routinely uses exactly these flags as a
gun/melee discriminator in functions that look gun-only at a glance.

**A fourth regression, on the AI side: "police don't melee the player."**
The same port's AI half (`CPed::KillCharOnFootMelee`, commit `4c7c4f4`)
added a PS2-faithful approach branch for non-fist melee weapons (seek the
victim's position, keep `max(0.4*range, 0.8)` away, skip
`FindMeleeAttackPoint`) — but the function's later attack gate was
`if (canReachVictim || !victimPlayer)`, and `canReachVictim` was only ever
set by the `FindMeleeAttackPoint` path the new branch skips. Result: every
non-fist melee AI (1-star nightstick cops, bat/knife gang members) ran up to
the player and stood ~2m away forever, never calling `SetAttack` — so cops
also never knocked the player down, and never reached the get-up-window
arrest. PS2's function (VA `0x31e0b0-0x31e860`; approach `0x31e1a4`, arrest
`0x31e348`, attack gate `0x31e51c-0x31e60c`) has **no reachability condition
at the gate at all**. Fix: `|| !isUnarmedOrBrassKnuckle` on the gate
(`stories/src/peds/PedAI.cpp`, test
`scripts/tests/test_ai_melee_attack_gate.py`). **Lesson:** when porting a
PS2 branch that *skips* a call, grep the rest of the function for every
local that call used to set (`canReachVictim` here) — the spec only said
"PS2 doesn't call it here," never what PS2 uses instead downstream. See
`git log --grep="non-fist melee"`.

## Case study: lock-on target selection ("autoaim too sensitive, snaps to far peds") — six small deltas, no single smoking gun

A user report of "autoaim snaps to something off-screen" / "locks too far
in general" did **not** resolve into one wrong constant. reLCS's gun
lock-on (`CPlayerPed::FindWeaponLockOnTarget`/`EvaluateTarget`/
`FindNextWeaponLockOnTarget`/`EvaluateNeighbouringTarget`,
`stories/src/peds/PlayerPed.cpp`) is byte-identical to `miami/`'s in every
constant that matters for raw range/angle (scoring formula
`-dist2D - 5*|angle| (+30 priority)`, the 40m `OurPedCanSeeThisOne` cap,
WEAPON.DAT ranges already matched the PS2 weapon table byte-for-byte —
confirmed by extracting PS2's own weapon table from `GAME.DAT` at offset
`0x40a980`, stride `0x70`). **Nothing in the obvious places was wrong.**
Disassembling PS2's equivalent functions found six separate, independent
behavior deltas instead, none of which alone was an obvious smoking gun:

1. **`EvaluateTarget` (PS2 VA `0x34d510`) has two scoring bonuses reLCS
   never had:** `+15.0` closeness if the candidate is on-screen (a call to
   `0x306008`, confirmed to be a `GetIsOnScreen()`-equivalent: reads
   `m_modelIndex` → `CModelInfo` → colmodel bounding sphere → a
   `TheCamera.IsSphereVisible`-style frustum test — reLCS already has the
   exact matching helper at `CEntity::GetIsOnScreen()`,
   `stories/src/entities/Entity.cpp:533-536`, just never wired into the
   score), and `+40.0` if the candidate is a ped with byte field `0x1ac ==
   2`. That field was identified as `CPed::CharCreatedBy` (`Ped.h:613`,
   confirmed by matching offsets, not by guessing) and `2` as
   `MISSION_CHAR` (`Ped.h:337`) — i.e. **PS2 actively prefers locking onto
   mission-relevant peds and onscreen peds over ordinary pedestrians**,
   which reLCS's pure distance/angle score has no equivalent for.
2. **The *initial* lock-on search's LOS check blocks shootable objects on
   PS2 but not in reLCS.** `FindWeaponLockOnTarget`'s ped loop called
   `OurPedCanSeeThisOne(pedToCheck)` (shootablesDoBlock defaulting false);
   PS2's equivalent call passes `shootablesDoBlock = true` here — matching
   what reLCS's own L/R-cycle variant (`FindNextWeaponLockOnTarget`)
   already did. The one-argument/two-argument call difference between two
   near-identical function names in the same file is exactly the kind of
   swap this skill's "generic one-argument setters" pitfall warns about —
   except here it was an *omitted* argument (defaulting to the wrong
   value) rather than a swapped VA.
3. **PS2 has a 6-frame cooldown after a lock-on target is lost, during
   which no new lock-on fires, and a forced re-lock the instant it
   expires if Target is still held** — found by tracing a byte field at
   CPlayerPed offset `0xc88` (decremented every frame in
   `ProcessPlayerWeapon`'s prologue, set to `6` whenever the lock-on gate
   fails while a target still exists, including on manual Target
   release). reLCS had no such field or delay at all — every frame with
   Target held re-evaluates fresh with no debounce, which if not costly
   on its own, combines with delta 1's on-screen bonus to let a stale,
   now-offscreen prior target get immediately replaced by whatever is
   currently onscreen even one frame later, producing a visibly "twitchy"
   re-lock.
4. **PS2 suppresses the *initial* lock-on trigger while L1 is held**, but
   only in `CPad::Mode` 0-2 (PS2 has 5 control schemes, 0-4; mode 4 remaps
   Target itself to L1, so the suppression doesn't apply there). reLCS's
   `CPad::GetTarget()`/`TargetJustDown()` already branch on `CURMODE`
   (reLCS has 4 schemes, 0-3, with mode 3 ≡ PS2's mode 4's L1-as-Target
   convention) for *which* button is Target, but had no L1-suppression
   logic at all for modes 0-2's schemes.
5. **PS2 allows L2/R2 target-cycling even with no current lock-on
   target**, by falling back to a *saved* last-known position (PS2 field
   `0xca0`, a `CVector`, populated whenever a target is dropped due to
   death or entering a vehicle — tracked by a companion flag at `0xc94`).
   reLCS's `FindNextWeaponLockOnTarget(CEntity *previousTarget, ...)`
   unconditionally dereferenced `previousTarget->GetPosition()`, so it was
   simply never callable with no target at all — not a wrong value, a
   missing code path.
6. **`EvaluateNeighbouringTarget` (PS2 VA `0x34d740`, the L/R-cycle
   scorer) has a hard 50° (`0.8727` rad) angular cutoff** reLCS's version
   never had — without it, the cycle button can "jump" to a candidate far
   outside the visually reasonable cone just because it has the smallest
   signed angle among *all* ped-pool entries, including ones behind or far
   to the side.

**Why this needed RE rather than source archaeology:** `miami/`'s
identical functions have exactly the same gaps (this is upstream-inherited
behavior, not a 3DS-port regression), so diffing against the sibling tree
found nothing — all three deltas affecting on-screen behavior are PS2-only
information with no equivalent anywhere in any existing fork.

**Fix shipped:** all six deltas ported in
`docs/superpowers/plans/2026-10-16-lock-on-ps2-parity.md` (full VAs, field
offsets, and exact diffs in the companion spec,
`docs/superpowers/specs/2026-10-16-lock-on-ps2-parity-design.md`), landing
as six small, independently-reviewed commits rather than one large diff —
each delta was independently falsifiable (a single call-site argument, a
single new field, a single early-out), which made this a good case for
task-per-delta decomposition instead of one "port the whole function"
task.

**A second-order bug this shipped alongside (see `AGENTS.md` landmine
#17):** the three new `CPlayerPed` fields needed to carry deltas 3 and 5
(a cooldown counter and a last-known-position fallback) grew
`sizeof(CPlayerPed)`, which silently broke every existing 3DS save file
(3DS saves are a raw, unversioned `memcpy` blob — see the landmine for the
full mechanism). **Adding new `CPlayerPed`/`CPed` fields while porting a
PS2 behavior delta is itself a landmine independent of whether the delta
is correctly ported** — budget an on-device load-an-old-save check into
the verification plan whenever a lock-on/ped-state RE fix adds fields, not
just a fresh-save smoke test.

**Lesson:** a "snaps to the wrong target" / "feels too sensitive" symptom
does not imply a single wrong range or angle constant — RE every function
in the target-selection pipeline (initial search, per-candidate scoring,
LOS gating, cycle-with-a-target, cycle-with-no-target, the frame-level
gate/cooldown around all of the above) independently, because PS2 GTA
engines routinely spread a dozen small, independently-motivated tweaks
across that whole pipeline rather than concentrating tuning in one
function.

## Case study: a single unique string disambiguates a one-line fix — and still surfaces two missed calls

Not every disassembly pass needs a jump table, a struct walk, or multiple
candidate functions. "The weapon-pickup swap prompt never shows up on 3DS"
resolved almost entirely from source first (`stories/src/control/Pickups.cpp`'s
`CPickup::Update` was asking `TheText.Get()` for VC-only GXT keys
`PU_CF1`/`PU_CF3`/`PU_CF4` that don't exist in LCS's compiled GXT — see
`AGENTS.md` landmine #19 for the full mechanism) — the disassembly pass was
only needed to confirm the one-line fix (`TheText.Get("PU_CF")`, no
per-mode switch) was actually what PS2 does, not a guess.

Because `PU_CF` is a 5-character ASCII literal that happens to be unique in
the whole ~3MB ELF, this was the simplest possible disambiguation case: a
plain byte search for `"PU_CF\0"` in the extracted `SLES_541.35` found
exactly one hit, and `find_addr_refs`-style tracing from that VA found
exactly one `lui`/`addiu` pair referencing it, inside exactly one function
(`CPickup::Update`, VA `0x1c7758`). No candidate-function ambiguity, no
struct-offset cross-checking needed — when a string constant is long enough
to be unique, confirming "is this the right call site" is a one-step search,
not a multi-step RE process like the case studies above.

That simplicity is exactly why it was worth doing anyway: reading the ~60
instructions around the single call site (disassembled in MIPS64 mode for
the R5900 `ld`/`sd` on the pickup's 64-bit flag word) turned up two
`CHud::SetHelpMessage(nil, ...)` calls — clearing the prompt immediately on
a collect-button press and immediately on stepping off the pickup — that
the source-only read of `Pickups.cpp` had no way to predict, because reLCS's
version of this function never had equivalent calls to begin with. A
source-only fix (just swap the GXT key) would have been *correct but
incomplete*: it would have fixed the missing text without fixing the
now-separately-noticeable "prompt lingers via its fade timeout instead of
disappearing instantly" behavior.

**Lesson:** even when a source-level bug is fully explained without the
ELF (wrong/missing key, wrong flag, wrong constant), a quick disassembly
pass of the PS2 equivalent — cheap here because the call site was found by
a unique-string search, not a multi-step RE process — can still reveal
adjacent behavior the port dropped silently, especially around anything
that shows/hides UI state (prompts, HUD messages, markers): those tend to
have a paired "clear" call on both the success and abandon paths, and a
port that only reimplements the "show" half rarely leaves a source-visible
trace of the missing "hide" half.

## Case study: PS2 follow-cam parity round 2 (yaw drift, Select zoom, L force-behind)

After `Process_FollowPed_Rotation` was ported from PS2 `MODE_FOLLOWPED`
(`0x281f50`), on-device testing reported yaw not holding while running,
Select not changing distance while standing, and L no longer forcing the
camera behind Toni. Full pseudocode of `0x281f50` (REA) settled all three;
details in `docs/superpowers/specs/2026-10-17-ps2-follow-cam-parity-fixes-design.md`.

- **PS2 is a cam-on-a-string with two LCS-only *virtual* sources** (CCam
  `0x220` far = `pivot - max(maxDist,4)*dir`, `0x230` near =
  `pivot - dist*dir`, both at `virtualPitch = Alpha-ish + lookDown`). Yaw
  each frame is driven toward the **string yaw** of the far source
  (`BetaSpeed` target = `(stringYaw + step - Beta)/max(dt,1)`), and the
  auto-rotate step is **proportional** (`min(1, 0.1*dt*|speed|) * Δ`,
  capped `±0.02*dt`). The first port used a constant-rate slew on Beta with
  no string term, which never settles — the "yaw drift". Note the real
  `Source` uses pitch `Alpha` only (camera looks at the pivot); `lookDown`
  only goes into the virtual sources — easy to conflate.
- **Select zoom**: string distance uses `floor = (maxDist > prevMaxDist) ?
  maxDist : 2.0`, so growing zoom pushes the camera out even when the ped is
  stationary. PS2 `m_fPedZoomValue` is `0.0/2.5/3.5` (reLCS had VC's
  `0.25/1.5/2.9`). PS2 `TheCamera` base is `0x43bdf0` (`+0x1cc` smooth zoom,
  `+0x1e4` PedZoomIndicator); `elf_tools refs` finds nothing for those
  fields because accesses go through the base pointer.
- **Wall whiskers**: 5 LOS rays (spacing 0.17, start `pivot-0.3*Front`)
  steer Beta by `(i-2)*0.03` per blocked ray while moving, decaying `0.95`;
  the main pull-in LOS only runs when all 5 are blocked, the stick (or
  force-behind) is active, or a 2-frame post-hit countdown is running.
- **Force-behind latch** (`gp-0x34`): `FUN_00172150` = ForceCameraBehindPlayer
  (returns false if `GetLookBehindForPed` (`FUN_00171470`) && ped state
  PED_ATTACK/PED_FIGHT; `0x34c` enum matches reLCS). Latched: k = `min(1,
  0.1*dt)` (speed ignored), cap `×2` (`gp-0x18`=2.0), no 170° gate, and when
  `bIsStanding` (`0x194` bit0) pitch levels toward 0 with cap `0.16*dt`.
  Clears when moving or `|Δ|<0.01`. EE `0x46020028`-style words are
  `max.s`/`min.s` (MMI-ish COP1 ops capstone can't decode).

**Lesson:** a mode-function replacement drops every input the old function
read (here `ForceCameraBehindPlayer`) — grep the replaced function's `CPad`
calls. And separately-found 3DS port code can mask parity issues: the D-pad
was dead in-game because port hotkeys zeroed it, not because of camera code.

## Case study: traffic lights stop cars dead — finding a compiled data table with no strings

Report: cars bounce off traffic lights on 3DS, smash through them on PS2.
The staged `DATA/OBJECT.DAT` (`trafficlight1`: 500kg, uproot 1200, effect 3)
is GTA III's file from the asset converter; the PS2 disc has no text copy.
PS2's table is compiled into `/CHK/PS2/GAME.DTZ` and the decompressed blob has
**no model-name strings** (hashed), so it was found by searching for the float
pattern of a known row (`600.0, 4000.0, 0.99` for `lamppost1`) — rows are
0x20 bytes near file offset `0x3d4890`, in III's row order, with buoyancy
already precomputed (`100/percentSubmerged * GRAVITY * mass`) and the three
int columns packed into bytes. Every relevant row matched III, which moved
the search from data to code.

PS2 `CObject::ObjectDamage` was located by `lui 0x4316` (150.0f, the damage
gate) at `0x221e84` → function `0x221e08`. It takes `(amount, this, colpoint)`
— one more argument than reLCS. A `jal 0x221e08` scan showed 13 callers, only
one (`0x2c0038`, ApplyCollision's static-object branch) passing a non-nil
colpoint. Effect 3 on PS2 does the full smash-completely teardown and spawns
`gpModelIndices` +2/+4/+6/+8 (`TLIGHT_POST/WALK/BOX1/BOX2`) as temp objects
at fixed local offsets, pushed by `amount * normal * 0.02`. **Lesson:** an
extra argument at the PS2 entry point that reLCS's signature lacks is a strong
hint a whole behavior was dropped; scan the callers to see which actually
pass it. Fix: `git log --grep="smash traffic lights"`.

## Case study: melee fight-system parity — diff the whole cluster, not one function

Report: "not confident melee works like PS2". Earlier melee fixes had each
patched one function; this pass decompiled every `PedFight.cpp` function's PS2
twin and diffed them side by side. Map (`SLES_541.35`): `Fight` `0x1beb80`,
next-move starter `0x1be938` (reLCS inlined it; now `StartNextFightMove`),
`StartFightAttack` `0x1bdbd8`, `StartFightDefend` `0x1bdf98` (takes the
attacker as an extra arg), `ChooseAttackPlayer` `0x1bf498`, `ChooseAttackAI`
`0x1bf170`, `EndFight` `0x1bff50`, `PlayHitSound` `0x1c00b8` (sound table
`0x3b4080`, 17×10 uint16, row = `m_curFightMove` directly), `FightStrike`
`0x1c0310`, `FightHitPed` `0x1c09e0`, `FinishFightMoveCB` `0x1c14c8`,
`ReactToAttack` `0x30e828`. Callers were found with `tools.rea.xrefs
({address})` on an already-known VA (e.g. the two callers of `0x1bf498`).

What differed was mostly **VC logic that LCS had rewritten**: strike is one
frame at `startFireTime + 0.05` (not a start..end window); combos chain via
the normal chooser once past `endFireTime` with pressure buffered (VC's
one-shot `nPlayerInComboMove` chain doesn't exist); AI unarmed moves are a
weighted `rand & 0xf` pick (no ped-stat flags); hit reactions are
direction-only, with `ANIM_FIGHT_HIT_A1..B3` matching the attacker's combo;
fight strikes damage cars (`TestSphereAgainstWorld` → `VehicleDamage` +
`OccupantsReactToDamage`); shoppers (MI 47, 59-61) never fight; `PlayHitSound`
(disabled in reLCS) also does the player's on-hit shout. `GAME.DTZ`'s compiled
fight-move table (file offset `0x3a3cec`) and weapon table matched the staged
`FISTFITE.DAT`/`WEAPON.DAT`, so none of this was data. See
`git log --grep="match PS2 LCS melee"`.

**Pitfall — the decompiler hid two branch targets.** Ghidra's pseudocode of
`ReactToAttack` showed the stripper wait-state branch as "ClearWaitState and
return"; the asm (`0x30eb68`) branches into the shared `KILL_CHAR_ON_FOOT` +
20 s timer block, so reLCS was already right. Check asm before reporting a
"PS2 skips this" delta.

**VC hardcodes compiled out as `== -1`.** PS2 LCS kept every VC
`m_nPedType == PEDTYPE_GANG7` (Vercetti, player-friendly) test but compares
against `-1`, which never matches: `lw v1,0x560(sX); li v0,-1; bne…` at
`0x30e8b0`, `0x30e398`, `0x3183a0`, `0x1c2088`. In LCS GANG7 is a hostile
gang, so reLCS's live checks made those peds harmless. A raw-word scan for
`lw *,0x560(*)` next to `addiu *,zero,-1` found all four sites. See
`git log --grep="GANG7"`.

**Ped "runs away instead of fighting" is usually PS2-correct.** Flee vs fight
is `victim.fear > 100 - attacker.temper` (player temper 50). `PEDSTATS.DAT`
and every model's ped/stat type in `DEFAULT.IDE` match PS2's compiled tables
(CPedModelInfo stride 0x44 in `GAME.DTZ`), and most common civilians have
fear 56-100. Check the data against PS2 before "fixing" AI aggression.

**Running punch whiffs: control flow matched PS2, the timing didn't.** A
punch pressed at `m_fMoveSpeed >= 1.0` goes through `SetAttack(nil)` →
`ANIM_MELEE_ATTACK_START` → `CPed::Attack` → `CWeapon::FireMelee`. This
split matches PS2 (`ProcessPlayerWeapon` `0x34b100`, `SetAttack` `0x1babe0`,
`FireMelee` `0x2a3360`). There were two bugs. First, reLCS had a VC-only
block that froze the start anim at 0.1 while the stick was held. PS2
`Attack` `0x1bc498` never reads `m_fMoveSpeed`, so the block was removed.
Second, `FIGHTppunch` is only 0.233 s long, and the anim-finish callback
cleared the attack before the 0.2 s fire frame could run (AGENTS.md
landmine #30). Lesson: once every function matches PS2 and a bug still
reproduces, measure the timing. Check anim lengths against single-frame
gates at the real frame rate. Also confirm the tested build contains the
fix (`git merge-base --is-ancestor <fix> <tested-branch>`) before you dig
further: one "still whiffs" report here came from a build without the
fix. See `git log --grep="running punch"`.

## Case study: scorched wrecks — tracing a `CEntity` bitfield flag to its readers

Wrecks kept their paint on 3DS. PS2 `BlowUpCar` (`0x137ba0`, found from its
`rand()%6000+4000` and `0.13f` immediates) writes no colour. It only sets
flags in the 64-bit word at `entity+0x40` (`ld`/`sd`; `m_status` is bits
36-40, `bRenderScorched` is bit 53, which is mask `0x00200000` in the word
at `+0x44`). Grep for tests of that bit to find the readers:
`SetupLighting` (`0x2c9f30`, and siblings `0x2ca060`/`0x2ca158`/`0x2ca250`) calls
`WorldReplaceNormalLightsWithScorched(0.1f)` (`0x184918`) and sets global
`gp+0xd78`. The vehicle env-map setup (`0x2e870c`/`0x2e8f48`) then does
`movn a2,$zero,<that global>`, so wrecks have no reflection. The 3DS bug was
not in game code. librw's 3DS MatFX and skin paths are unlit and ignored that
lighting (AGENTS.md landmine #28). When PS2 does a visual effect through RW
lights, check that the 3DS render path actually reads the lights.

The first fix used 0.1 x paint and wrecks came out almost black; on PS2 a
taxi wreck is clearly mustard yellow. **PS2 ambient light counts double.**
Per-atomic light setup (`0x1850c0`) uploads ambient with `0x184e60`:
`int(colour*255)`, then `sll 1`, clamp to 255. Directional lights go through
`0x184f40` with no doubling. `0x3562f0` copies the light state to VU1. The
lighting microcode is embedded in `.text` (`0x272800` compressed normals,
`0x272cf0` float normals, pointer table `0x39a9a8`), not in `.vutext` (that
one is collision code): it scales each light by `material * 1/510`
(`LOI 0x3b008081`), sums ambient + N.L, clamps to 255 and writes the vertex
colour, which GS modulate reads with 128 = 1.0. So the scorched 0.1 ambient
shows as 0.2 x texture x paint. A PS2 screenshot agrees: hood pixel
`(40,30,5)` for taxi paint `(255,182,16)`, i.e. a body texture of ~0.8.
Ghidra's EE language can't decode VU micro mode; a small decoder of the
upper/lower 32-bit pairs was enough to read it.

## Case study: island load screens on the water — same data, different lookup

In "Caught in the Act" (GXT `SALS3`, a boat mission down the Portland/Staunton
channel) the Portland and Staunton loading screens kept showing. PS2 has the
same mechanism: `CStreaming::LoadBigBuildingsWhenNeeded` (`0x18b760`, only
caller `Update` `0x18ae60`) does the blocking big-building swap and
`LoadingIslandScreen` (`0x1f58b8`, splash table `0x3927b8` =
`{0,"splash1","splash2","splash3","loadsc0"}`) whenever
`CTheZones::m_CurrLevel` differs from `CGame::currLevel` (`gp+0x2d64`). So the
question was why `m_CurrLevel` flips on 3DS and not on PS2.

The zone data is not the cause. PS2's map zones are compiled into
`GAME.DTZ` (0x38-byte records starting at `THEMAP`, decompressed offset
`0x324a50`: name[8], min xyz `+8`, max xyz `+0x14`, type `+0x20`, level
`+0x24`). All 103 match `DATA/GTA3.ZON`, in the same order. The difference is
`GetLevelFromPosition` (`0x2d3b20`). reLCS returned the first containing zone.
PS2 does this:

```
level = GENERIC;
for each containing map zone i >= 1:
    if(zone.level == CGame::currLevel) return it;      // stay on the current island
    if(level == GENERIC || currLevel == 4 || zone.level != 4) level = zone.level;
return level;
```

Island zones overlap a lot in the channel, so "stay if any containing zone
is the current island" is hysteresis. reLCS switched islands up to 8 times
along the route; the PS2 rule switches at most once. Read the delay slots
carefully here: the `movz` that makes "first match wins" is in the delay slot
of `bne currLevel,4`, so it always runs. Skipping that delay slot gives a
wrong rule where level 4 is ignored. `IPL` buildings also get their level
from this function (PS2 stores it at entity `+0x5a` in `GAME.DTZ`). Checked
against PS2: 49 buildings got the right island after the fix and none got
worse. Fix: `stories/src/core/Zones.cpp`, test
`scripts/tests/test_zone_level_from_position.py`; see
`git log --grep="island load screens"`.

## Case study: map waypoint blip — the look lives in the sprite texture

Report: the map waypoint was a grey triangle on 3DS and a red hollow square on
PS2. reLCS's `ToggleTargetMarker` made a dim grey sprite-less coord blip, so
`DrawCoordBlip` picked a triangle or square from player height (waypoint z is
0). PS2 `0x119120` (called from the frontend toggle `0x33fac8`) fills the first
free `ms_RadarTrace` slot with colour 0 (red), bright flag `+0x32` = 1, scale 1,
`BLIP_ONLY` and sprite `0x31` = `mp_objective`. There is no "hollow square"
draw code: the shape is the texture itself (11×11 white ring with black
outline in `hud.txd`). `DrawCoordBlip` `0x115fe4` forces alpha 255 for sprite
`0x31` and draws via the tinted sprite draw `0x119eb0` (colour from
`GetRadarTraceColour` `0x119aa0` = 255,72,77). `DrawLegend` `0x116760` shows it
as `LG_54` "Player Target", tinted pure red (`0x1167b4`).

Lesson: when a blip's shape looks wrong, dump the `RadarSprites[]` table from
`LoadTextures` (`0x115548`) and look at the texture before writing a new
primitive. Fix: `stories/src/core/Radar.cpp`, test
`scripts/tests/test_waypoint_blip.py`.

## Case study: script-sound ids — VC's enum reused for LCS's script numbers

Report: entering any Ammu-Nation played a gunshot. Each shop script
(`INDAMMU`, `COMAMMU`, `SUBAMMU`) plays `ADD_ONE_OFF_SOUND x,y,z,52` (or 53,
alternating per visit) at the door. reLCS read those ids through VC's
`eScriptSounds`, where 52/53 are `BULLET_HIT_GROUND_1/2`. On PS2 they are the
shop greeting samples `SFX_AMMU_AA/AB`.

- PS2 `ADD_ONE_OFF_SOUND` (~`0x20a25c`) sends a few ids to
  `PlayFrontEndSound` (1, 7-10, 13, 14, 16, 0x46, 0x47). Every other id becomes
  a `cAudioScriptObject` → `CreateOneShotScriptObject` (`0x2a2120`).
- Audio path: `ProcessEntity` `0x19eb40` (switch on entity type; 4 =
  `ProcessScriptObject` `0x1b1d60`). That calls
  `ProcessOneShotScriptObject` `0x1b1de8` or `ProcessLoopingScriptObject`
  `0x1b2a90`. `ProcessFrontEnd` is `0x1b32f8`. `cAudioManager` lives at
  `0x42d2a0` and `PlayOneShot` at `0x238458`. `cDMAudio::PlayOneShot` is
  `0x2a1f40` (130 callers; scan its `jal`s to find who emits an eSound id).
- **PS2 sample indices equal reLCS `AudioSamples.h` values exactly.**
  Check them by compiling the enum (`printf("%d", SFX_X)`). Don't count
  lines: the awk line-count method was wrong here.
- LCS one-shot layout: ids 0-51 match VC. 52-54 are AMMU_AA/AB/AC, 55-61
  C_OR_D_UNK, 62/63 DOCK_BA/BB, 64/65 COLT45, 66 PIZZA_THROW, 67 R_OR_S_UNK1,
  68/69 GATE_START/STOP_CLU and 70/71 frontend. VC's 52-67 tail
  (bullet-hit-ground … gunshell drop) moves to 72-87. Looping ids still
  match VC.
- PS2 `eSound` has 208 entries; reLCS had 204. 204 is the ped crunch
  (chainsaw contact, player dying in a car), 205 the frontend `SFX_BEEP`
  (script id 71), 206 the car-jacked victim whoosh. 203 and 207 are dead. The
  one-shot priority table is 208 bytes at `0x392830`.
- C++ emitters use the enum names, so renumbering the enum fixed them all at
  once. Only literal ids from `main.scm` were wrong. To audit, scan
  `main.scm` for opcodes 0x191/0x192 and list their literal ids.

Lesson: an enum inherited from VC that a data file indexes by number (script
ids, `main.scm` literals) can be wrong past some point even when every C++
use is fine. Get the PS2 handler's case list before trusting the enum. See
`docs/superpowers/specs/2026-10-24-lcs-script-sound-ids-design.md` and
`git log --grep="script-sound"`.
