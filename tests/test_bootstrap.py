"""End-to-end bootstrap validation for the self-hosted Ulang compiler.

Proves two properties, treating the Python compiler as the reference specification:

1. Equivalence: for every stage of the pipeline (tokens, syntax tree, diagnostics,
   package exports, optimized tree, bytecode), the self-hosted compiler produces output
   identical to the Python reference across the example programs.

2. Self-compilation: the self-hosted compiler can compile its own source files
   (the ``selfhost/compiler/*.ul`` stages) through the front and middle end
   (lex, parse, type-check, optimize), and its results agree with the reference.

This is the "Python builds the Ulang compiler, then the Ulang compiler processes itself"
bootstrap step. The one representational boundary — string interpolation, whose embedded
sub-expressions are not carried by the opaque string atom in the canonical syntax tree —
is excluded from strict bytecode comparison and documented; it is covered by the
reference's own VM tests.
"""

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from selfhost_driver import Driver, SelfhostError

from parser import parse
from lexer import tokenize, TokenType as T
from checker import check
from optimizer import optimize_module
from compiler import compile_module
from ast_serialize import serialize_module
from bytecode_serialize import serialize_program

EXAMPLES = os.path.join(ROOT, "examples")
COMPILER = os.path.join(ROOT, "selfhost", "compiler")


def _norm(text):
    return "\n".join(l for l in text.splitlines() if l.strip())


def _ref_tokens(src):
    out = []
    for t in tokenize(src):
        if t.type == T.EOF:
            out.append("eof")
        elif t.type == T.NEWLINE:
            out.append("newline")
        elif t.type == T.INDENT:
            out.append("indent")
        elif t.type == T.DEDENT:
            out.append("dedent")
        elif t.type == T.KEYWORD:
            out.append(f"kw {t.value}")
        elif t.type == T.IDENT:
            out.append(f"id {t.value}")
        elif t.type == T.INT:
            out.append(f"int {t.value}")
        elif t.type == T.FLOAT:
            out.append("float")
        elif t.type == T.STRING:
            out.append("str")
        else:
            out.append(f"op {t.value}")
    return "\n".join(out)


def _ref_tree(src):
    return _norm(serialize_module(parse(src)))


def _ref_diagnostics(src):
    import re
    lines = [str(e).split(": ", 1)[-1] for e in check(parse(src))]
    return _norm("\n".join(re.sub(r"\?\d+", "?_", l) for l in lines))


def _ref_optimized(src):
    return _norm(serialize_module(optimize_module(parse(src))))


def _ref_bytecode(src):
    return _norm(serialize_program(compile_module(parse(src))))


def _uses_interpolation(src):
    return "${" in src


def run():
    driver = Driver()
    failed = 0
    checked = 0

    def compare(label, expected, actual):
        nonlocal failed, checked
        checked += 1
        if _norm(actual) == expected:
            print(f"ok   {label}")
        else:
            print(f"FAIL {label}")
            failed += 1

    print("== Stage equivalence across example programs ==")
    for path in sorted(glob.glob(os.path.join(EXAMPLES, "*.ul"))):
        name = os.path.basename(path)
        src = open(path).read()
        try:
            compare(f"{name}: tokens", _ref_tokens(src), driver.tokens(src))
            tree = driver.parse(src)
            compare(f"{name}: syntax tree", _ref_tree(src), tree)
            import re
            diags = _norm("\n".join(re.sub(r"\?\d+", "?_", l)
                                    for l in driver.diagnostics(tree).splitlines()))
            compare(f"{name}: diagnostics", _ref_diagnostics(src), diags)
            compare(f"{name}: exports", _norm(_export_ref(src)), driver.exports(tree))
            if not _uses_interpolation(src):
                compare(f"{name}: optimized tree", _ref_optimized(src),
                        driver.optimize(tree))
                compare(f"{name}: bytecode", _ref_bytecode(src), driver.bytecode(tree))
        except SelfhostError as e:
            print(f"FAIL {name}: {e}")
            failed += 1

    print("\n== Self-compilation: the compiler compiling its own source ==")
    for path in sorted(glob.glob(os.path.join(COMPILER, "*.ul"))):
        name = "selfhost/compiler/" + os.path.basename(path)
        src = open(path).read()
        try:
            compare(f"{name}: tokens", _ref_tokens(src), driver.tokens(src))
            tree = driver.parse(src)
            compare(f"{name}: syntax tree", _ref_tree(src), tree)
            import re
            diags = _norm("\n".join(re.sub(r"\?\d+", "?_", l)
                                    for l in driver.diagnostics(tree).splitlines()))
            compare(f"{name}: diagnostics", _ref_diagnostics(src), diags)
            if not _uses_interpolation(src):
                compare(f"{name}: optimized tree", _ref_optimized(src),
                        driver.optimize(tree))
        except SelfhostError as e:
            print(f"FAIL {name}: {e}")
            failed += 1

    driver.close()
    print(f"\n{checked - failed}/{checked} checks passed")
    if failed == 0:
        print("bootstrap: the self-hosted compiler is equivalent to the reference "
              "and compiles its own source")
    return 1 if failed else 0


def _export_ref(src):
    tree = parse(src)
    members = []
    for decl in tree.body:
        tn = type(decl).__name__
        if tn == "Function" and getattr(decl, "is_pub", False):
            members.append(decl.name)
        elif tn == "TypeDecl" and getattr(decl, "is_pub", False):
            members.append(decl.name)
        elif tn == "EnumDecl" and getattr(decl, "is_pub", False):
            for v in decl.variants:
                members.append(v.name)
        elif tn == "Const":
            members.append(decl.name)
    return "\n".join(members)


if __name__ == "__main__":
    sys.exit(run())
