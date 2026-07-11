import os

from values import Module, Closure


MODULES_DIR = "ulang_modules"
MANIFEST_FILE = "ulang.toml"


def find_package(name, search_roots):
    for root in search_roots:
        pkg_dir = os.path.join(root, MODULES_DIR, name)
        if os.path.isdir(pkg_dir):
            return pkg_dir
    return None


def _entry_path(pkg_dir):
    manifest_path = os.path.join(pkg_dir, MANIFEST_FILE)
    entry = "src/main.ul"
    if os.path.exists(manifest_path):
        from manifest import Manifest
        try:
            entry = Manifest.load(manifest_path).entry
        except Exception:
            pass
    candidates = [entry, "src/lib.ul", "src/main.ul"]
    for rel in candidates:
        full = os.path.join(pkg_dir, rel)
        if os.path.exists(full):
            return full
    return None


def load_package(name, search_roots, interpreter_cls):
    pkg_dir = find_package(name, search_roots)
    if pkg_dir is None:
        return None
    entry = _entry_path(pkg_dir)
    if entry is None:
        return None
    from parser import parse
    with open(entry, "r", encoding="utf-8") as f:
        source = f.read()
    tree = parse(source)
    sub = interpreter_cls()
    sub.collect_library(tree)
    members = {}
    for decl in tree.body:
        type_name = type(decl).__name__
        if type_name == "Function" and getattr(decl, "is_pub", False):
            members[decl.name] = sub.globals.get(decl.name)
        elif type_name == "TypeDecl" and getattr(decl, "is_pub", False):
            members[decl.name] = sub.globals.get(decl.name)
        elif type_name == "EnumDecl" and getattr(decl, "is_pub", False):
            for variant in decl.variants:
                members[variant.name] = sub.globals.get(variant.name)
        elif type_name == "Const":
            members[decl.name] = sub.globals.get(decl.name)
    return Module(name, members)
