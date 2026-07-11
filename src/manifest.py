import re


class ManifestError(Exception):
    pass


def parse_toml(text):
    data = {}
    current = data
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            current = data
            for part in section.split("."):
                current = current.setdefault(part.strip(), {})
            continue
        if "=" not in line:
            raise ManifestError(f"invalid line: {raw!r}")
        key, value = line.split("=", 1)
        current[key.strip()] = _parse_value(value.strip())
    return data


def _parse_value(text):
    if text.startswith('"') and text.endswith('"'):
        return _unescape(text[1:-1])
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_value(p.strip()) for p in _split_list(inner)]
    if text in ("true", "false"):
        return text == "true"
    if re.match(r"^-?\d+$", text):
        return int(text)
    return text


def _split_list(text):
    parts = []
    depth = 0
    buf = []
    in_str = False
    for ch in text:
        if ch == '"':
            in_str = not in_str
        if ch == "[" and not in_str:
            depth += 1
        elif ch == "]" and not in_str:
            depth -= 1
        if ch == "," and depth == 0 and not in_str:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _unescape(text):
    return text.replace('\\"', '"').replace("\\\\", "\\")


def _escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def dump_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f'"{_escape(value)}"'
    if isinstance(value, list):
        return "[" + ", ".join(dump_value(v) for v in value) + "]"
    raise ManifestError(f"cannot serialize {value!r}")


class Manifest:
    def __init__(self, data=None):
        self.data = data or {}

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            return cls(parse_toml(f.read()))

    @classmethod
    def loads(cls, text):
        return cls(parse_toml(text))

    @property
    def name(self):
        return self.data.get("package", {}).get("name")

    @property
    def version(self):
        return self.data.get("package", {}).get("version")

    @property
    def entry(self):
        return self.data.get("package", {}).get("entry", "src/main.ul")

    @property
    def description(self):
        return self.data.get("package", {}).get("description", "")

    @property
    def license(self):
        return self.data.get("package", {}).get("license", "")

    def dependencies(self):
        return dict(self.data.get("dependencies", {}))

    def set_dependency(self, name, constraint):
        self.data.setdefault("dependencies", {})[name] = constraint

    def remove_dependency(self, name):
        deps = self.data.get("dependencies", {})
        existed = name in deps
        deps.pop(name, None)
        return existed

    def validate(self):
        pkg = self.data.get("package")
        if not pkg:
            raise ManifestError("missing [package] section")
        if not pkg.get("name"):
            raise ManifestError("missing package name")
        if not pkg.get("version"):
            raise ManifestError("missing package version")
        name = pkg["name"]
        if not re.match(r"^[a-z][a-z0-9_-]*$", name):
            raise ManifestError(f"invalid package name: {name!r}")
        from semver import Version
        Version.parse(pkg["version"])

    def dumps(self):
        lines = []
        pkg = self.data.get("package", {})
        lines.append("[package]")
        for key in ("name", "version", "description", "entry", "license"):
            if key in pkg:
                lines.append(f"{key} = {dump_value(pkg[key])}")
        for key, value in pkg.items():
            if key not in ("name", "version", "description", "entry", "license"):
                lines.append(f"{key} = {dump_value(value)}")
        lines.append("")
        lines.append("[dependencies]")
        for name, constraint in self.dependencies().items():
            lines.append(f"{name} = {dump_value(constraint)}")
        return "\n".join(lines) + "\n"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.dumps())
