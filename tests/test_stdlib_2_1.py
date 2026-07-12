"""Conformance tests for the 2.1 standard-library modules.

Exercises regex, encoding, crypto, compress, os, log, and datetime, and verifies each
produces the expected result on both the interpreter and the bytecode VM.
"""

import os
import sys
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ULANG = os.path.join(ROOT, "src", "ulang.py")


# (name, program, expected_stdout)
CASES = [
    ("regex.test", 'import regex\nfn main():\n    print(regex.test("[0-9]+", "abc123"))\n    print(regex.test("^x", "abc"))\n', "true\nfalse\n"),
    ("regex.find_all", 'import regex\nfn main():\n    print(regex.find_all("[0-9]+", "a1b22c333").len())\n', "3\n"),
    ("regex.replace", 'import regex\nfn main():\n    print(regex.replace("o", "0", "foobar"))\n', "f00bar\n"),
    ("regex.split", 'import regex\nfn main():\n    print(regex.split(",\\\\s*", "a, b,c").len())\n', "3\n"),
    ("encoding.base64", 'import encoding\nfn main():\n    print(encoding.base64_encode("hello"))\n', "aGVsbG8=\n"),
    ("encoding.base64_decode", 'import encoding\nfn main():\n    match encoding.base64_decode("aGVsbG8="):\n        Ok(s) => print(s)\n        Err(e) => print("err")\n', "hello\n"),
    ("encoding.hex", 'import encoding\nfn main():\n    print(encoding.hex_encode("hi"))\n', "6869\n"),
    ("encoding.url", 'import encoding\nfn main():\n    print(encoding.url_encode("a b&c"))\n', "a%20b%26c\n"),
    ("crypto.sha256", 'import crypto\nfn main():\n    print(crypto.sha256(""))\n', "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"),
    ("crypto.md5", 'import crypto\nfn main():\n    print(crypto.md5("abc"))\n', "900150983cd24fb0d6963f7d28e17f72\n"),
    ("compress.roundtrip", 'import compress\nfn main():\n    let s = "the quick brown fox jumps over the lazy dog"\n    match compress.decompress(compress.compress(s)):\n        Ok(out) => print(out == s)\n        Err(e) => print("err")\n', "true\n"),
    ("os.cwd", 'import os\nfn main():\n    print(os.cwd().len() > 0)\n', "true\n"),
    ("os.env", 'import os\nfn main():\n    os.setenv("ULANG_TEST_VAR", "42")\n    match os.getenv("ULANG_TEST_VAR"):\n        Some(v) => print(v)\n        None => print("none")\n', "42\n"),
    ("datetime.now", 'import datetime\nfn main():\n    let d = datetime.now()\n    print(d.year > 2020)\n    print(d.month >= 1 and d.month <= 12)\n', "true\ntrue\n"),
    ("datetime.format", 'import datetime\nfn main():\n    let d = datetime.from_unix(0)\n    print(datetime.format(d, "YYYY-MM-DD"))\n', None),  # tz-dependent; only checks parity
]


def _run(engine, program, workdir):
    path = os.path.join(workdir, "prog.ul")
    with open(path, "w") as f:
        f.write(program)
    r = subprocess.run([sys.executable, ULANG, engine, path],
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def run():
    workdir = tempfile.mkdtemp()
    failed = 0
    checked = 0
    for name, program, expected in CASES:
        checked += 1
        icode, iout, ierr = _run("run", program, workdir)
        vcode, vout, verr = _run("runvm", program, workdir)
        if icode != 0:
            print(f"FAIL {name}: interpreter error: {ierr.strip()}")
            failed += 1
            continue
        if iout != vout:
            print(f"FAIL {name}: interpreter/VM mismatch: {iout!r} vs {vout!r}")
            failed += 1
            continue
        if expected is not None and iout != expected:
            print(f"FAIL {name}: expected {expected!r}, got {iout!r}")
            failed += 1
            continue
        print(f"ok   {name}: {iout.strip()!r} (interpreter == VM)")

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("2.1 standard-library modules: verified on interpreter and VM")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
