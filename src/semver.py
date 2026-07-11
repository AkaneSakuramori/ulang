import re


_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


class Version:
    __slots__ = ("major", "minor", "patch", "prerelease")

    def __init__(self, major, minor, patch, prerelease=None):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease

    @classmethod
    def parse(cls, text):
        m = _VERSION_RE.match(text.strip())
        if not m:
            raise ValueError(f"invalid version: {text!r}")
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4))

    def _key(self):
        pre = self.prerelease
        if pre is None:
            return (self.major, self.minor, self.patch, 1, ())
        parts = tuple((0, int(p)) if p.isdigit() else (1, p) for p in pre.split("."))
        return (self.major, self.minor, self.patch, 0, parts)

    def __eq__(self, other):
        return isinstance(other, Version) and self._key() == other._key()

    def __lt__(self, other):
        return self._key() < other._key()

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        return not self <= other

    def __ge__(self, other):
        return not self < other

    def __hash__(self):
        return hash(self._key())

    def __str__(self):
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base

    def __repr__(self):
        return f"Version({self})"


class Constraint:
    def __init__(self, text):
        self.text = text.strip()
        self.checks = self._compile(self.text)

    def _compile(self, text):
        if text in ("", "*", "any"):
            return []
        if text.startswith("^"):
            return self._caret(Version.parse(text[1:]))
        if text.startswith("~"):
            return self._tilde(Version.parse(text[1:]))
        for op in (">=", "<=", ">", "<", "="):
            if text.startswith(op):
                v = Version.parse(text[len(op):])
                return [(op, v)]
        return [("=", Version.parse(text))]

    def _caret(self, v):
        if v.major > 0:
            upper = Version(v.major + 1, 0, 0)
        elif v.minor > 0:
            upper = Version(0, v.minor + 1, 0)
        else:
            upper = Version(0, 0, v.patch + 1)
        return [(">=", v), ("<", upper)]

    def _tilde(self, v):
        return [(">=", v), ("<", Version(v.major, v.minor + 1, 0))]

    def matches(self, version):
        if isinstance(version, str):
            version = Version.parse(version)
        for op, ref in self.checks:
            if op == "=" and not version == ref:
                return False
            if op == ">=" and not version >= ref:
                return False
            if op == "<=" and not version <= ref:
                return False
            if op == ">" and not version > ref:
                return False
            if op == "<" and not version < ref:
                return False
        return True

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"Constraint({self.text!r})"


def best_match(constraint, versions):
    matching = [v for v in versions if constraint.matches(v)]
    if not matching:
        return None
    return max(matching)
