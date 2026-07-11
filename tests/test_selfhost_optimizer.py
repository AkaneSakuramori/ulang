import os
import sys
import glob
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from parser import parse
from optimizer import optimize_module
from ast_serialize import serialize_module

COMPILER = os.path.join(ROOT, "selfhost", "compiler")
ULANG = os.path.join(ROOT, "src", "ulang.py")
EXAMPLES = os.path.join(ROOT, "examples")


# Corpus exercising every optimizer pass on int/bool/structural programs.
# (Constant folding of opaque string/float literals is a property of the
# reference's literal-preserving AST, not representable in the S-expression
# pipeline the self-hosted compiler consumes; those cases are excluded and
# documented, and covered separately by the reference's own optimizer tests.)
CASES = [
    "fn main():\n    let x = 2 + 3 * 4\n    print(x)\n",
    "fn main():\n    let x = 10 / 2 - 1\n    print(x)\n",
    "fn main():\n    let x = 7 % 3\n    print(x)\n",
    "fn main():\n    print(1 < 2)\n",
    "fn main():\n    print(2 == 2)\n",
    "fn main():\n    print(true and false)\n",
    "fn main():\n    print(true or false)\n",
    "fn main():\n    print(not true)\n",
    "fn main():\n    print(-5 + 3)\n",
    "fn main():\n    let x = 5\n    let y = x + 0\n    let z = y * 1\n    print(z)\n",
    "fn main():\n    let a = 0 + 9\n    let b = 1 * 7\n    print(a + b)\n",
    "const K = 10\nfn main():\n    let x = K * 2 + 1\n    print(x)\n",
    "const A = 3\nconst B = A + 2\nfn main():\n    print(B)\n",
    "fn main():\n    if true:\n        print(1)\n    else:\n        print(2)\n",
    "fn main():\n    if false:\n        print(1)\n    else:\n        print(2)\n",
    "fn main():\n    if 1 < 2:\n        print(1)\n",
    "fn main():\n    while false:\n        print(1)\n    print(2)\n",
    "fn main():\n    let x = 3 if true else 4\n    print(x)\n",
    "fn main():\n    let x = 3 if false else 4\n    print(x)\n",
    "fn f(n: int) -> int:\n    if n < 0:\n        return 0\n    elif n == 0:\n        return 1\n    else:\n        return 2\n",
    "fn main():\n    if false:\n        print(1)\n    elif true:\n        print(2)\n    else:\n        print(3)\n",
    "fn main():\n    if false:\n        print(1)\n    elif false:\n        print(2)\n    elif 2 > 1:\n        print(3)\n",
    "fn main():\n    var s = 0\n    for i in range(0, 3):\n        s += i * 1\n    print(s)\n",
    "fn main():\n    let f = x => x + 0\n    print(f)\n",
    "fn main():\n    match k:\n        A => print(1 + 1)\n        _ => print(0)\n",
    "fn main():\n    let xs = [1 + 1, 2 * 3, 4 - 1]\n    print(xs)\n",
    "fn main():\n    let d = {1 + 1: 2 * 2}\n    print(d)\n",
    "fn main():\n    let t = (1 + 1, 2 + 2)\n    print(t)\n",
    "fn main():\n    return\n    print(1)\n",
    "const RATE = 3\nfn main():\n    var total = 0\n    for i in range(0, 10):\n        total += RATE * 1 + 0\n    print(total)\n",
]


def reference(src):
    return serialize_module(optimize_module(parse(src)))


def selfhosted(src, workdir):
    with open(os.path.join(workdir, "input.ul"), "w") as f:
        f.write(src)
    tree = subprocess.run([sys.executable, ULANG, "run", "parser.ul"],
                          cwd=workdir, capture_output=True, text=True)
    if tree.returncode != 0:
        raise RuntimeError("parser: " + tree.stderr.strip())
    with open(os.path.join(workdir, "tree.sexpr"), "w") as f:
        f.write(tree.stdout)
    opt = subprocess.run([sys.executable, ULANG, "run", "optimizer.ul"],
                         cwd=workdir, capture_output=True, text=True)
    if opt.returncode != 0:
        raise RuntimeError("optimizer: " + opt.stderr.strip())
    return opt.stdout.rstrip("\n")


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(os.path.join(COMPILER, "parser.ul"), os.path.join(workdir, "parser.ul"))
    shutil.copy(os.path.join(COMPILER, "optimizer.ul"), os.path.join(workdir, "optimizer.ul"))
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
            print(f"ok   case[{idx}]: optimized tree matches reference")
        else:
            print(f"FAIL case[{idx}]:")
            print(f"     reference:   {expected}")
            print(f"     self-hosted: {actual}")
            failed += 1

    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        name = os.path.basename(path)
        src = open(path).read()
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL {name}: {e}")
            failed += 1
            continue
        checked += 1
        if actual == expected:
            print(f"ok   {name}: optimized tree matches reference")
        else:
            print(f"FAIL {name}: optimized tree differs")
            failed += 1

    if not _fuzz(workdir):
        failed += 1
    checked += 1

    print(f"\n{checked - failed}/{checked} passed")
    if failed == 0:
        print("self-hosting Stage 3 (optimizer): optimized trees match the reference")
    return 1 if failed else 0


def _fuzz(workdir, count=40, seed=13):
    import random
    rng = random.Random(seed)

    def expr(depth):
        if depth <= 0 or rng.random() < 0.4:
            r = rng.random()
            if r < 0.7:
                return str(rng.randint(0, 12))
            return rng.choice(["true", "false"])
        op = rng.choice(["+", "-", "*", "/", "%", "<", ">", "==", "!=", "and", "or"])
        return f"({expr(depth - 1)} {op} {expr(depth - 1)})"

    for _ in range(count):
        n = rng.randint(1, 4)
        stmts = [f"    let v{j} = {expr(rng.randint(1, 3))}" for j in range(n)]
        src = "fn main():\n" + "\n".join(stmts) + "\n    print(v0)\n"
        expected = reference(src)
        try:
            actual = selfhosted(src, workdir)
        except RuntimeError as e:
            print(f"FAIL fuzz: {e}")
            return False
        if actual != expected:
            print(f"FAIL fuzz on:\n{src}  reference:   {expected}\n  self-hosted: {actual}")
            return False
    print(f"ok   fuzz: {count} random int/bool programs optimize identically")
    return True


if __name__ == "__main__":
    sys.exit(run())
