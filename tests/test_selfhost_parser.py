import os
import sys
import shutil
import tempfile
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from lexer import tokenize
from parser import Parser
import ast_nodes as ast


EXPR_PARSER_UL = os.path.join(ROOT, "selfhost", "expr_parser.ul")
ULANG = os.path.join(ROOT, "src", "ulang.py")


CORPUS = [
    "1 + 2 * 3",
    "2 * 3 + 4",
    "1 - 2 - 3",
    "10 / 2 / 5",
    "1 + 2 + 3 + 4",
    "-x + 1",
    "-(a + b)",
    "not a",
    "not a == b",
    "a and b or c",
    "a or b and c",
    "a == b == c",
    "a < b + c",
    "f(1, 2 + 3)",
    "f(g(x), y)",
    "a.b.c",
    "obj.method(1)",
    "xs[0] + 1",
    "m[i][j]",
    "[1, 2, 3]",
    "[a + b, c * d]",
    "x if c else y",
    "a if b else c if d else e",
    "(1 + 2) * 3",
    "1 * (2 + 3) * 4",
    "a and not b",
    "p.q[0].r",
    "f(a)(b)",
]


def reference_sexpr(expr):
    p = Parser(tokenize(expr + "\n"))
    node = p.parse_expr()
    return _ser(node)


def _ser(node):
    if isinstance(node, ast.Int):
        return str(node.value)
    if isinstance(node, ast.Bool):
        return "true" if node.value else "false"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.BinOp):
        return f"({node.op} {_ser(node.left)} {_ser(node.right)})"
    if isinstance(node, ast.UnaryOp):
        op = "neg" if node.op == "-" else node.op
        return f"({op} {_ser(node.operand)})"
    if isinstance(node, ast.Call):
        parts = [_ser(node.func)] + [_ser(a.value) for a in node.args]
        return "(call " + " ".join(parts) + ")"
    if isinstance(node, ast.Index):
        return f"(index {_ser(node.target)} {_ser(node.index)})"
    if isinstance(node, ast.Attribute):
        return f"(attr {_ser(node.target)} {node.name})"
    if isinstance(node, ast.ListLit):
        if not node.elements:
            return "(list)"
        return "(list " + " ".join(_ser(e) for e in node.elements) + ")"
    if isinstance(node, ast.Ternary):
        return f"(ternary {_ser(node.cond)} {_ser(node.then)} {_ser(node.orelse)})"
    raise AssertionError(f"unsupported node {type(node).__name__}")


def ulang_sexpr(expr, workdir):
    with open(os.path.join(workdir, "input.txt"), "w") as f:
        f.write(expr)
    result = subprocess.run(
        [sys.executable, ULANG, "run", "expr_parser.ul"],
        cwd=workdir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def run():
    workdir = tempfile.mkdtemp()
    shutil.copy(EXPR_PARSER_UL, os.path.join(workdir, "expr_parser.ul"))
    failed = 0
    for expr in CORPUS:
        expected = reference_sexpr(expr)
        try:
            actual = ulang_sexpr(expr, workdir)
        except RuntimeError as e:
            print(f"FAIL {expr!r}: ulang parser error: {e}")
            failed += 1
            continue
        if actual == expected:
            print(f"ok   {expr:<26} => {expected}")
        else:
            print(f"FAIL {expr!r}")
            print(f"     ulang:  {actual}")
            print(f"     python: {expected}")
            failed += 1
    total = len(CORPUS)
    print(f"\n{total - failed}/{total} passed")
    if failed == 0:
        print("self-hosting: the Ulang expression parser matches the reference AST")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
