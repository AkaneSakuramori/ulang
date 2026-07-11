import sys
sys.path.insert(0, "src")

from bytecode import Op
from values import Variant

# Canonical, textual serialization of a compiled bytecode function, used to compare the
# self-hosted bytecode generator against the reference. LOAD_CONST is rendered by value
# (not pool index) and MATCH_VARIANT by a canonical pattern form, so the comparison does
# not depend on incidental representation choices.

_NAME_OPS = {Op.LOAD_NAME, Op.STORE_NAME, Op.ASSIGN_NAME, Op.GET_ATTR, Op.SET_ATTR}
_OP_OPS = {Op.BINARY, Op.UNARY}
_JUMP_OPS = {Op.JUMP, Op.JUMP_IF_FALSE, Op.JUMP_IF_TRUE}
_COUNT_OPS = {Op.CALL, Op.BUILD_LIST, Op.BUILD_DICT, Op.BUILD_TUPLE, Op.BUILD_STRING}


def render_const(v):
    if v is None:
        return "unit"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, Variant) and v.enum_name == "Option" and v.name == "None":
        return "none"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return "(flt)"
    if isinstance(v, str):
        return "(str)"
    return "(?)"


def render_pattern(p):
    import ast_nodes as ast
    if isinstance(p, ast.WildcardPattern):
        return "_"
    if isinstance(p, ast.BindPattern):
        return p.name
    if isinstance(p, ast.LiteralPattern):
        return "(litp)"
    if isinstance(p, ast.VariantPattern):
        return f"(vp {p.name} {len(p.args)})"
    if isinstance(p, ast.TuplePattern):
        return f"(tp {len(p.elements)})"
    return "(?)"


def render_code(code, indent=0):
    pad = "  " * indent
    lines = []
    params = ",".join(code.params)
    lines.append(f"{pad}code {code.name} [{params}]")
    for i, ins in enumerate(code.instrs):
        op = ins.op
        arg = ins.arg
        if op == Op.LOAD_CONST:
            text = f"LOAD_CONST {render_const(code.consts[arg])}"
        elif op in _NAME_OPS:
            text = f"{op.name} {arg}"
        elif op in _OP_OPS:
            text = f"{op.name} {arg}"
        elif op in _JUMP_OPS:
            text = f"{op.name} {arg}"
        elif op in _COUNT_OPS:
            text = f"{op.name} {arg}"
        elif op == Op.MATCH_VARIANT:
            text = f"MATCH_VARIANT {render_pattern(arg)}"
        elif op == Op.MAKE_CLOSURE:
            text = "MAKE_CLOSURE"
            lines.append(f"{pad}  {i}: {text}")
            lines.append(render_code(arg, indent + 2))
            continue
        else:
            text = op.name
        lines.append(f"{pad}  {i}: {text}")
    return "\n".join(lines)


def serialize_program(program):
    out = []
    for name in program.functions:
        out.append(render_code(program.functions[name]))
    return "\n".join(out)


if __name__ == "__main__":
    from parser import parse
    from compiler import compile_module
    src = open(sys.argv[1]).read()
    print(serialize_program(compile_module(parse(src))))
