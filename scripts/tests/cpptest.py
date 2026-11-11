"""Shared helpers for the host-compiled C++ regression tests.

Tests extract real function bodies from the game source, splice them into a
harness under scripts/tests/cpp/ (which can #include "stubs.h" for common fake
engine types), then compile and run the result with the host `c++`.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CPP_DIR = Path(__file__).resolve().parent / "cpp"


class SourceText(str):
    """File contents that remember which file they came from, for error messages."""

    def __new__(cls, text, name):
        obj = super().__new__(cls, text)
        obj.name = name
        return obj


def read_source(rel):
    """Read a repo-relative file, e.g. read_source('stories/src/core/Pad.cpp')."""
    return SourceText((ROOT / rel).read_text(), rel)


def _find(source, needle, start, what):
    pos = source.find(needle, start)
    if pos < 0:
        name = getattr(source, "name", "<source>")
        raise AssertionError(f"{what} {needle!r} not found in {name} -- was it renamed or reformatted?")
    return pos


def extract_function(source, signature):
    """Return the function starting at `signature`, up to and including the
    next column-zero closing brace."""
    start = _find(source, signature, 0, "signature")
    end = _find(source, "\n}", start, f"closing brace of {signature!r}:") + len("\n}")
    return source[start:end] + "\n"


def between(source, start, end, include_end=False):
    """Return the text from `start` up to `end` (excluding it unless include_end)."""
    s = _find(source, start, 0, "start marker")
    e = _find(source, end, s + len(start), f"end marker after {start!r}:")
    return source[s:e + len(end) if include_end else e]


def strip_comments(code):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", code, flags=re.S))


def harness(name, **parts):
    """Read scripts/tests/cpp/<name> and replace each `/*@KEY@*/` marker with parts[KEY]."""
    text = (CPP_DIR / name).read_text()
    for key, value in parts.items():
        marker = f"/*@{key}@*/"
        if marker not in text:
            raise AssertionError(f"marker {marker} not found in scripts/tests/cpp/{name}")
        text = text.replace(marker, value)
    left = re.findall(r"/\*@\w+@\*/", text)
    if left:
        raise AssertionError(f"unfilled markers in scripts/tests/cpp/{name}: {left}")
    return text


def _compile(cpp_source, tmp, sanitize, flags):
    path, binary = Path(tmp) / "test.cpp", Path(tmp) / "test"
    path.write_text(cpp_source)
    cmd = ["c++", "-std=c++11", "-I", str(CPP_DIR)]
    if sanitize:
        cmd.append("-fsanitize=address,undefined")
    cmd += list(flags) + [str(path), "-o", str(binary)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        numbered = "\n".join(f"{i:4}: {line}" for i, line in enumerate(cpp_source.splitlines(), 1))
        raise AssertionError(f"compile failed:\n{result.stderr}\n--- generated source ---\n{numbered}")
    return binary


def _run(binary, args, env):
    result = subprocess.run([str(binary), *args], capture_output=True, text=True,
                            env=dict(os.environ, **(env or {})))
    if result.returncode != 0:
        raise AssertionError(f"test binary exited {result.returncode}\n"
                             f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result.stdout


def compile_and_run(cpp_source, sanitize=True, env=None, flags=(), args=()):
    """Compile `cpp_source` and run it once; returns stdout. Fails with the
    compiler output or the program's stderr (e.g. the failed assert)."""
    with tempfile.TemporaryDirectory(prefix="regta-cpptest-") as tmp:
        return _run(_compile(cpp_source, tmp, sanitize, flags), args, env)


class Program:
    """Compile once, run many times (e.g. one scenario name per argv)."""

    def __init__(self, cpp_source, sanitize=True, flags=()):
        self._tmp = tempfile.TemporaryDirectory(prefix="regta-cpptest-")
        self._binary = _compile(cpp_source, self._tmp.name, sanitize, flags)

    def run(self, *args, env=None):
        return _run(self._binary, args, env)

    def close(self):
        self._tmp.cleanup()
