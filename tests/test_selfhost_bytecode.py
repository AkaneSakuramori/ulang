import os
import sys
import glob
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from parser import parse
from compiler import compile_module
from bytecode_serialize import serialize_program

COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")
EXAMPLES = os.path.join(ROOT, "examples")


# Programs exercising every bytecode form. String interpolation is excluded because the
# self-hosted pipeline's canonical syntax-tree form treats string literals as opaque
# atoms (the interpolated sub-expressions are not represented); that boundary is the same
# one documented for the parser and optimizer, and interpolation codegen is covered by the
# reference's own VM tests.
CASES = [
    "fn f(n: int) -> int:\n    return n + 1\n",
    "fn f(n: int) -> int:\n    if n < 2:\n        return n\n    return f(n - 1) + f(n - 2)\n",
    "fn main():\n    var s = 0\n    for i in range(0, 10):\n        s += i\n    print(s)\n",
    "fn main():\n    var n = 5\n    while n > 0:\n        n -= 1\n    print(n)\n",
    "fn main():\n    let xs = [1, 2, 3]\n    print(xs[0])\n",
    "fn main():\n    let d = {1: 2, 3: 4}\n    print(d[1])\n",
    "fn main():\n    let t = (1, 2, 3)\n    print(t)\n",
    "fn main():\n    let (a, b) = (1, 2)\n    print(a + b)\n",
    "fn main():\n    print(1 + 2 * 3 - 4)\n",
    "fn main():\n    print(true and false or true)\n",
    "fn main():\n    print(not (1 < 2))\n",
    "fn main():\n    let x = 3 if true else 4\n    print(x)\n",
    "fn f(n: int) -> int:\n    if n < 0:\n        return 0\n    elif n == 0:\n        return 1\n    else:\n        return 2\n",
    "fn main():\n    var i = 0\n    while true:\n        i += 1\n        if i > 5:\n            break\n        continue\n    print(i)\n",
    "fn main():\n    let sq = x => x * x\n    print(sq(5))\n",
    "fn main():\n    let add = (a, b) => a + b\n    print(add(2, 3))\n",
    "fn make() -> dyn:\n    var c = 0\n    return () => {\n        c += 1\n        return c\n    }\n",
    "enum E:\n    A(int)\n    B\nfn f(e: dyn) -> int:\n    match e:\n        A(x) => x\n        B => 0\n",
    "fn main():\n    let r = Ok(1)\n    match r:\n        Ok(v) => print(v)\n        Err(e) => print(e)\n",
    "fn main():\n    let xs = [1, 2, 3]\n    let ys = xs.map(x => x * 2).filter(x => x > 2)\n    print(ys)\n",
    "fn main():\n    var a = [0, 0]\n    a[0] = 5\n    a[1] += 3\n    print(a)\n",
    "type P:\n    x: int\nfn main():\n    var p = P(1)\n    p.x = 9\n    print(p.x)\n",
    "fn g() -> Result[int, str]:\n    let v = h()?\n    return Ok(v)\nfn h() -> Result[int, str]:\n    return Ok(5)\n",
    "fn main():\n    with open() as fh:\n        defer close()\n        print(fh)\n",
    "const K = 10\nfn main():\n    print(K + 5)\n",
]


def reference(src):
    return serialize_program(compile_module(parse(src)))


def selfhosted(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    bc = subprocess.run([sys.executable, ULANG, "run", "bytecode.ul"],
                        cwd=workdir, capture_output=True, text=True)
    if bc.returncode != 0:
        raise RuntimeError("bytecode: " + bc.stderr.strip())
    return bc.stdout.rstrip("\n")


def _uses_interpolation(src):
    return "${" in src


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "bytecode.ul"), os.path.join(workdir, "bytecode.ul"))
    failed = 0
    checked = 0

    for idx, src in enumerate(CASES):
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL case[{idx}]: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   case[{idx}]: bytecode matches reference")
        else:
            print(f"FAIL case[{idx}]:")
            _first_diff(expected, actual)
            failed += 1

    skipped = 0
    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        name = os.path.basename(path)
        src = open(path).read()
        if _uses_interpolation(src):
            skipped += 1
            continue
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   {name}: bytecode matches reference")
        else:
            print(f"FAIL {name}: bytecode differs")
            _first_diff(expected, actual)
            failed += 1

    print(f"\n{checked - failed}/{checked} passed "
          f"({skipped} interpolation-using examples excluded by representation)")
    if failed == 0:
        print("self-hosting Stage 3 (bytecode generation): matches the reference")
    return 1 if failed else 0


def _first_diff(expected, actual):
    e = expected.splitlines()
    a = actual.splitlines()
    for i in range(min(len(e), len(a))):
        if e[i] != a[i]:
            print(f"     line {i}: reference {e[i]!r}")
            print(f"              self-hosted {a[i]!r}")
            return
    if len(e) != len(a):
        print(f"     length {len(a)} vs {len(e)}")


if __name__ == "__main__":
    sys.exit(run())
