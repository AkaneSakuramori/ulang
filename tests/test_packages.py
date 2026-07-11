import os
import sys
import io
import shutil
import tempfile
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from semver import Version, Constraint, best_match
from manifest import Manifest, ManifestError
from registry import Registry, RegistryError, sha256_bytes
from resolver import resolve_dependencies, ResolutionError
from lockfile import Lockfile
from packages import Project, PackageError
from parser import parse
from interpreter import Interpreter


def publish(registry, name, version, deps, body="pub fn value() -> int:\n    return 1\n"):
    files = {
        "ulang.toml": f'[package]\nname = "{name}"\nversion = "{version}"\nentry = "src/lib.ul"\n',
        "src/lib.ul": body,
    }
    registry.publish(name, Version.parse(version), f"{name} pkg", deps, files)


def run_ulang(src, root):
    interp = Interpreter()
    interp.search_roots = [root]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        interp.run(parse(src))
    return buf.getvalue().strip()


def test_semver():
    assert Version.parse("1.2.3") < Version.parse("1.10.0")
    assert Version.parse("1.0.0-alpha") < Version.parse("1.0.0")
    assert Constraint("^1.2.0").matches("1.9.0")
    assert not Constraint("^1.2.0").matches("2.0.0")
    assert Constraint("~1.2.0").matches("1.2.5")
    assert not Constraint("~1.2.0").matches("1.3.0")
    assert best_match(Constraint("^1.0.0"),
                      [Version.parse(v) for v in ["1.1.0", "1.9.0", "2.0.0"]]) == Version.parse("1.9.0")
    return "semver: ordering, caret, tilde, best-match"


def test_manifest_roundtrip():
    m = Manifest.loads('[package]\nname = "x"\nversion = "1.0.0"\n\n[dependencies]\na = "^1.0.0"\n')
    m.validate()
    m.set_dependency("b", "~2.0.0")
    m2 = Manifest.loads(m.dumps())
    assert m2.dependencies() == {"a": "^1.0.0", "b": "~2.0.0"}
    try:
        Manifest.loads('[package]\nname = "1bad"\nversion = "1.0.0"\n').validate()
        return None
    except ManifestError:
        pass
    return "manifest: roundtrip + name validation"


def test_publish_and_checksum():
    reg = Registry(tempfile.mkdtemp())
    publish(reg, "acme", "1.0.0", {})
    assert reg.exists("acme")
    reg.verify_artifact("acme", Version.parse("1.0.0"))
    try:
        publish(reg, "acme", "1.0.0", {})
        return None
    except RegistryError:
        pass
    return "registry: publish, checksum verify, immutable versions"


def test_tamper_detection():
    reg = Registry(tempfile.mkdtemp())
    publish(reg, "secure", "1.0.0", {})
    path = reg._artifact_path("secure", Version.parse("1.0.0"))
    with open(path, "ab") as f:
        f.write(b"evil")
    try:
        reg.verify_artifact("secure", Version.parse("1.0.0"))
        return None
    except RegistryError:
        return "security: tampered artifact rejected by checksum"


def test_resolution_and_conflict():
    reg = Registry(tempfile.mkdtemp())
    publish(reg, "core", "1.0.0", {})
    publish(reg, "core", "1.1.0", {})
    publish(reg, "util", "1.0.0", {"core": "^1.0.0"})
    resolved = resolve_dependencies(reg, {"util": "^1.0.0"})
    assert str(resolved["core"]) == "1.1.0"
    publish(reg, "pin", "1.0.0", {"core": "=1.0.0"})
    both = resolve_dependencies(reg, {"util": "^1.0.0", "pin": "^1.0.0"})
    assert str(both["core"]) == "1.0.0"
    publish(reg, "core", "2.0.0", {})
    publish(reg, "needs2", "1.0.0", {"core": "=2.0.0"})
    try:
        resolve_dependencies(reg, {"pin": "^1.0.0", "needs2": "^1.0.0"})
        return None
    except ResolutionError:
        pass
    return "resolver: transitive, convergence, conflict detection"


def test_full_workflow():
    reg_root = tempfile.mkdtemp()
    os.environ["ULANG_REGISTRY"] = reg_root
    reg = Registry(reg_root)
    publish(reg, "greeter", "1.0.0", {},
            body="pub fn hi(name: str) -> str:\n    return \"hi ${name}\"\n")

    app = tempfile.mkdtemp()
    os.makedirs(os.path.join(app, "src"))
    with open(os.path.join(app, "ulang.toml"), "w") as f:
        f.write('[package]\nname = "app"\nversion = "0.1.0"\n')
    with open(os.path.join(app, "src", "main.ul"), "w") as f:
        f.write('import greeter\nfn main():\n    print(greeter.hi("bob"))\n')

    project = Project(app, reg)
    project.add("greeter", None)
    assert os.path.exists(os.path.join(app, "ulang.lock"))
    assert os.path.isdir(os.path.join(app, "ulang_modules", "greeter"))

    out = run_ulang(open(os.path.join(app, "src", "main.ul")).read(), app)
    assert out == "hi bob", out
    return "workflow: add -> lock -> install -> import-and-run"


def test_reproducible_and_lock_integrity():
    reg = Registry(tempfile.mkdtemp())
    publish(reg, "dep", "1.0.0", {})
    app = tempfile.mkdtemp()
    os.makedirs(os.path.join(app, "src"))
    with open(os.path.join(app, "ulang.toml"), "w") as f:
        f.write('[package]\nname = "a"\nversion = "0.1.0"\n\n[dependencies]\ndep = "^1.0.0"\n')
    with open(os.path.join(app, "src", "main.ul"), "w") as f:
        f.write("fn main():\n    print(1)\n")
    project = Project(app, reg)
    project.install()
    lock1 = open(os.path.join(app, "ulang.lock")).read()
    project.install()
    lock2 = open(os.path.join(app, "ulang.lock")).read()
    assert lock1 == lock2

    lock = Lockfile.load(os.path.join(app, "ulang.lock"))
    lock.packages["dep"]["checksum"] = "0" * 64
    lock.save(os.path.join(app, "ulang.lock"))
    try:
        Project(app, reg)._materialize(lock)
        return None
    except PackageError:
        pass
    return "reproducible: identical lock + lockfile checksum enforced"


def test_remove_prunes_orphans():
    reg = Registry(tempfile.mkdtemp())
    publish(reg, "leaf", "1.0.0", {})
    publish(reg, "branch", "1.0.0", {"leaf": "^1.0.0"})
    app = tempfile.mkdtemp()
    os.makedirs(os.path.join(app, "src"))
    with open(os.path.join(app, "ulang.toml"), "w") as f:
        f.write('[package]\nname = "a"\nversion = "0.1.0"\n\n[dependencies]\nbranch = "^1.0.0"\n')
    with open(os.path.join(app, "src", "main.ul"), "w") as f:
        f.write("fn main():\n    print(1)\n")
    project = Project(app, reg)
    project.install()
    assert os.path.isdir(os.path.join(app, "ulang_modules", "leaf"))
    project.remove("branch")
    assert not os.path.exists(os.path.join(app, "ulang_modules", "branch"))
    assert not os.path.exists(os.path.join(app, "ulang_modules", "leaf"))
    return "remove: prunes transitive orphans"


TESTS = [
    test_semver,
    test_manifest_roundtrip,
    test_publish_and_checksum,
    test_tamper_detection,
    test_resolution_and_conflict,
    test_full_workflow,
    test_reproducible_and_lock_integrity,
    test_remove_prunes_orphans,
]


def run():
    failed = 0
    for t in TESTS:
        try:
            result = t()
            if result is None:
                print(f"FAIL {t.__name__}: assertion returned None")
                failed += 1
            else:
                print(f"ok   {result}")
        except Exception as e:
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    total = len(TESTS)
    print(f"\n{total - failed}/{total} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
