import json

from semver import Version


LOCK_VERSION = 1


class Lockfile:
    def __init__(self, packages=None):
        self.packages = packages or {}

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data.get("packages", {}))

    def save(self, path):
        payload = {
            "lockfile_version": LOCK_VERSION,
            "packages": dict(sorted(self.packages.items())),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")

    @classmethod
    def from_resolution(cls, registry, resolved):
        packages = {}
        for name, version in resolved.items():
            entry = registry.release(name, version)
            packages[name] = {
                "version": str(version),
                "checksum": entry["checksum"],
                "dependencies": dict(entry.get("dependencies", {})),
            }
        return cls(packages)

    def entries(self):
        return dict(self.packages)

    def checksum(self, name):
        return self.packages[name]["checksum"]

    def version(self, name):
        return self.packages[name]["version"]

    def __eq__(self, other):
        return isinstance(other, Lockfile) and self.packages == other.packages
