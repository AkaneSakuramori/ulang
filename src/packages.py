import os
import shutil

from manifest import Manifest, ManifestError
from registry import Registry, collect_package_files, RegistryError
from resolver import resolve_dependencies
from lockfile import Lockfile
from semver import Version


MODULES_DIR = "ulang_modules"
MANIFEST_FILE = "ulang.toml"
LOCK_FILE = "ulang.lock"


class PackageError(Exception):
    pass


class Project:
    def __init__(self, root, registry=None):
        self.root = root
        self.registry = registry or Registry()

    @property
    def manifest_path(self):
        return os.path.join(self.root, MANIFEST_FILE)

    @property
    def lock_path(self):
        return os.path.join(self.root, LOCK_FILE)

    @property
    def modules_path(self):
        return os.path.join(self.root, MODULES_DIR)

    def manifest(self):
        if not os.path.exists(self.manifest_path):
            raise PackageError(f"no {MANIFEST_FILE} in {self.root}")
        return Manifest.load(self.manifest_path)

    def _resolve_and_lock(self, manifest):
        resolved = resolve_dependencies(self.registry, manifest.dependencies())
        lock = Lockfile.from_resolution(self.registry, resolved)
        lock.save(self.lock_path)
        return lock

    def _load_or_build_lock(self, manifest, force_resolve=False):
        if force_resolve or not os.path.exists(self.lock_path):
            return self._resolve_and_lock(manifest)
        lock = Lockfile.load(self.lock_path)
        if not self._lock_satisfies(manifest, lock):
            return self._resolve_and_lock(manifest)
        return lock

    def _lock_satisfies(self, manifest, lock):
        from semver import Constraint
        entries = lock.entries()
        for name, spec in manifest.dependencies().items():
            if name not in entries:
                return False
            if not Constraint(spec).matches(entries[name]["version"]):
                return False
        return True

    def install(self, force_resolve=False):
        manifest = self.manifest()
        manifest.validate()
        lock = self._load_or_build_lock(manifest, force_resolve)
        installed = self._materialize(lock)
        return lock, installed

    def _materialize(self, lock):
        installed = []
        wanted = set(lock.entries().keys())
        for name, entry in lock.entries().items():
            version = Version.parse(entry["version"])
            actual = self.registry.verify_artifact(name, version)
            if actual != entry["checksum"]:
                raise PackageError(
                    f"lockfile checksum mismatch for {name} {version}"
                )
            dest = os.path.join(self.modules_path, name)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            self.registry.extract(name, version, dest)
            installed.append((name, str(version)))
        self._prune(wanted)
        return installed

    def _prune(self, wanted):
        if not os.path.isdir(self.modules_path):
            return
        for name in os.listdir(self.modules_path):
            if name not in wanted:
                path = os.path.join(self.modules_path, name)
                if os.path.isdir(path):
                    shutil.rmtree(path)

    def add(self, name, constraint=None):
        manifest = self.manifest()
        if not self.registry.exists(name):
            raise PackageError(f"package '{name}' not found in registry")
        if constraint is None:
            latest = max(self.registry.versions(name))
            constraint = f"^{latest}"
        manifest.set_dependency(name, constraint)
        manifest.save(self.manifest_path)
        return self.install(force_resolve=True)

    def remove(self, name):
        manifest = self.manifest()
        if not manifest.remove_dependency(name):
            raise PackageError(f"'{name}' is not a dependency")
        manifest.save(self.manifest_path)
        dest = os.path.join(self.modules_path, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        return self.install(force_resolve=True)

    def update(self):
        manifest = self.manifest()
        if os.path.exists(self.lock_path):
            os.remove(self.lock_path)
        return self.install(force_resolve=True)

    def publish(self):
        manifest = self.manifest()
        manifest.validate()
        name = manifest.name
        version = Version.parse(manifest.version)
        if self.registry.exists(name):
            if version in self.registry.versions(name):
                raise PackageError(f"{name} {version} is already published")
        files = collect_package_files(self.root, manifest.entry)
        if not any(k.endswith(".ul") for k in files):
            raise PackageError("no .ul source files to publish")
        checksum = self.registry.publish(
            name, version, manifest.description, manifest.dependencies(), files
        )
        return name, str(version), checksum

    def installed(self):
        result = []
        if not os.path.isdir(self.modules_path):
            return result
        for name in sorted(os.listdir(self.modules_path)):
            pkg_manifest = os.path.join(self.modules_path, name, MANIFEST_FILE)
            version = "?"
            if os.path.exists(pkg_manifest):
                try:
                    version = Manifest.load(pkg_manifest).version or "?"
                except ManifestError:
                    pass
            result.append((name, version))
        return result
