import os
import json
import hashlib
import tarfile
import io

from semver import Version, Constraint


class RegistryError(Exception):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def default_registry_path():
    env = os.environ.get("ULANG_REGISTRY")
    if env:
        return env
    return os.path.join(os.path.expanduser("~"), ".ulang", "registry")


class Registry:
    def __init__(self, root=None):
        self.root = root or default_registry_path()

    def _index_path(self, name):
        return os.path.join(self.root, name, "index.json")

    def _package_dir(self, name):
        return os.path.join(self.root, name)

    def _artifact_path(self, name, version):
        return os.path.join(self.root, name, f"{name}-{version}.tar")

    def exists(self, name):
        return os.path.exists(self._index_path(name))

    def load_index(self, name):
        path = self._index_path(name)
        if not os.path.exists(path):
            raise RegistryError(f"package not found: {name}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def versions(self, name):
        index = self.load_index(name)
        return [Version.parse(entry["version"]) for entry in index["releases"]]

    def release(self, name, version):
        index = self.load_index(name)
        target = str(version)
        for entry in index["releases"]:
            if entry["version"] == target:
                return entry
        raise RegistryError(f"{name} {version} not found")

    def resolve_version(self, name, constraint):
        c = constraint if isinstance(constraint, Constraint) else Constraint(constraint)
        matching = [v for v in self.versions(name) if c.matches(v)]
        if not matching:
            return None
        return max(matching)

    def dependencies_of(self, name, version):
        entry = self.release(name, version)
        return entry.get("dependencies", {})

    def artifact_bytes(self, name, version):
        path = self._artifact_path(name, version)
        if not os.path.exists(path):
            raise RegistryError(f"artifact missing for {name} {version}")
        with open(path, "rb") as f:
            return f.read()

    def verify_artifact(self, name, version):
        entry = self.release(name, version)
        data = self.artifact_bytes(name, version)
        actual = sha256_bytes(data)
        if actual != entry["checksum"]:
            raise RegistryError(
                f"checksum mismatch for {name} {version}: "
                f"expected {entry['checksum']}, got {actual}"
            )
        return actual

    def search(self, query):
        results = []
        if not os.path.isdir(self.root):
            return results
        for name in sorted(os.listdir(self.root)):
            index_path = self._index_path(name)
            if not os.path.exists(index_path):
                continue
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            desc = index.get("description", "")
            if query.lower() in name.lower() or query.lower() in desc.lower():
                latest = max(Version.parse(e["version"]) for e in index["releases"])
                results.append({"name": name, "version": str(latest), "description": desc})
        return results

    def publish(self, name, version, description, dependencies, files):
        pkg_dir = self._package_dir(name)
        os.makedirs(pkg_dir, exist_ok=True)
        data = _make_tar(files)
        checksum = sha256_bytes(data)
        with open(self._artifact_path(name, version), "wb") as f:
            f.write(data)

        index_path = self._index_path(name)
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"name": name, "description": description, "releases": []}
        index["description"] = description
        for entry in index["releases"]:
            if entry["version"] == str(version):
                raise RegistryError(f"{name} {version} already published")
        index["releases"].append({
            "version": str(version),
            "checksum": checksum,
            "dependencies": dependencies,
        })
        index["releases"].sort(key=lambda e: Version.parse(e["version"]))
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        return checksum

    def extract(self, name, version, dest):
        self.verify_artifact(name, version)
        data = self.artifact_bytes(name, version)
        os.makedirs(dest, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tar:
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name.split("/"):
                    raise RegistryError(f"unsafe path in artifact: {member.name}")
            tar.extractall(dest)


def _make_tar(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for relpath, content in sorted(files.items()):
            if isinstance(content, str):
                content = content.encode("utf-8")
            info = tarfile.TarInfo(name=relpath)
            info.size = len(content)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def collect_package_files(root, entry):
    files = {}
    manifest_path = os.path.join(root, "ulang.toml")
    if os.path.exists(manifest_path):
        with open(manifest_path, "rb") as f:
            files["ulang.toml"] = f.read()
    src_dir = os.path.join(root, "src")
    if os.path.isdir(src_dir):
        for base, _, names in os.walk(src_dir):
            for fn in sorted(names):
                if fn.endswith(".ul"):
                    full = os.path.join(base, fn)
                    rel = os.path.relpath(full, root).replace(os.sep, "/")
                    with open(full, "rb") as f:
                        files[rel] = f.read()
    return files
