import math as _math
import time as _time
import random as _random

import values as V
from values import Module, Builtin, Struct, some, ok, err, NONE, ulang_str


class FileHandle(V.UlangValue):
    __slots__ = ("path", "fp", "mode")

    def __init__(self, path, mode):
        self.path = path
        self.mode = mode
        self.fp = open(path, mode, encoding="utf-8")

    def __repr__(self):
        return f"<file {self.path}>"


def _fs_read(args):
    path = args[0]
    try:
        with open(path, "r", encoding="utf-8") as f:
            return ok(f.read())
    except OSError as e:
        return err(str(e))


def _fs_write(args):
    path, data = args[0], args[1]
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(ulang_str(data))
        return ok(None)
    except OSError as e:
        return err(str(e))


def _fs_open(args):
    path = args[0]
    mode = args[1] if len(args) > 1 else "w"
    return _FileValue(path, mode)


class _FileValue(V.UlangValue):
    __slots__ = ("path", "fp")

    def __init__(self, path, mode):
        self.path = path
        self.fp = open(path, mode, encoding="utf-8")

    def method(self, name):
        if name == "write":
            return Builtin("write", lambda a: (self.fp.write(ulang_str(a[0])), None)[1])
        if name == "read":
            return Builtin("read", lambda a: self.fp.read())
        if name == "close":
            return Builtin("close", lambda a: self.fp.close())
        return None

    def __repr__(self):
        return f"<file {self.path}>"


def _fs_exists(args):
    import os
    return __import__("os").path.exists(args[0])


def _json_dumps(args):
    import json as _json
    return _json.dumps(_to_plain(args[0]))


def _json_loads(args):
    import json as _json
    return _from_plain(_json.loads(args[0]))


def _to_plain(value):
    if isinstance(value, Struct):
        return {k: _to_plain(v) for k, v in value.fields.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    return value


def _from_plain(value):
    if isinstance(value, dict):
        return {k: _from_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_from_plain(v) for v in value]
    return value


FS = Module("fs", {
    "read": Builtin("read", _fs_read),
    "write": Builtin("write", _fs_write),
    "open": Builtin("open", _fs_open),
    "exists": Builtin("exists", _fs_exists),
})

JSON = Module("json", {
    "dumps": Builtin("dumps", _json_dumps),
    "loads": Builtin("loads", _json_loads),
})

MATH = Module("math", {
    "sqrt": Builtin("sqrt", lambda a: _math.sqrt(a[0])),
    "pow": Builtin("pow", lambda a: _math.pow(a[0], a[1])),
    "floor": Builtin("floor", lambda a: int(_math.floor(a[0]))),
    "ceil": Builtin("ceil", lambda a: int(_math.ceil(a[0]))),
    "abs": Builtin("abs", lambda a: abs(a[0])),
    "sin": Builtin("sin", lambda a: _math.sin(a[0])),
    "cos": Builtin("cos", lambda a: _math.cos(a[0])),
    "tan": Builtin("tan", lambda a: _math.tan(a[0])),
    "log": Builtin("log", lambda a: _math.log(a[0], a[1]) if len(a) > 1 else _math.log(a[0])),
    "exp": Builtin("exp", lambda a: _math.exp(a[0])),
    "min": Builtin("min", lambda a: min(a[0], a[1])),
    "max": Builtin("max", lambda a: max(a[0], a[1])),
    "round": Builtin("round", lambda a: int(_math.floor(a[0] + 0.5))),
    "pi": _math.pi,
    "e": _math.e,
})


TIME = Module("time", {
    "now": Builtin("now", lambda a: _time.time()),
    "now_ms": Builtin("now_ms", lambda a: int(_time.time() * 1000)),
    "sleep": Builtin("sleep", lambda a: _sleep_ms(a[0])),
})

STR = Module("str", {
    "from_int": Builtin("from_int", lambda a: str(a[0])),
    "to_int": Builtin("to_int", lambda a: _parse_int(a[0])),
    "repeat": Builtin("repeat", lambda a: a[0] * a[1]),
    "join": Builtin("join", lambda a: a[0].join(ulang_str(x) for x in a[1])),
})

RANDOM = Module("random", {
    "int": Builtin("int", lambda a: _random.randint(a[0], a[1] - 1)),
    "float": Builtin("float", lambda a: _random.random()),
    "choice": Builtin("choice", lambda a: _random.choice(a[0])),
    "seed": Builtin("seed", lambda a: _random.seed(a[0])),
})

LIST = Module("list", {
    "range": Builtin("range", lambda a: list(range(a[0], a[1]))),
    "repeat": Builtin("repeat", lambda a: [a[0]] * a[1]),
    "concat": Builtin("concat", lambda a: a[0] + a[1]),
})


def _sleep_ms(ms):
    _time.sleep(ms / 1000.0)
    return None


def _parse_int(s):
    try:
        return ok(int(s))
    except ValueError:
        return err(f"invalid int: {s}")


# --- 2.1 ecosystem modules -------------------------------------------------

def _regex_module():
    import re as _re

    def _search(a):
        m = _re.search(a[0], a[1])
        return some(m.group(0)) if m else NONE

    def _match(a):
        return _re.fullmatch(a[0], a[1]) is not None

    def _find_all(a):
        return _re.findall(a[0], a[1])

    def _replace(a):
        # replace(pattern, replacement, text)
        return _re.sub(a[0], a[1], a[2])

    def _split(a):
        return _re.split(a[0], a[1])

    def _groups(a):
        m = _re.search(a[0], a[1])
        if not m:
            return NONE
        return some(list(m.groups()))

    def _test(a):
        return _re.search(a[0], a[1]) is not None

    return Module("regex", {
        "test": Builtin("test", _test),
        "search": Builtin("search", _search),
        "match": Builtin("match", _match),
        "find_all": Builtin("find_all", _find_all),
        "replace": Builtin("replace", _replace),
        "split": Builtin("split", _split),
        "groups": Builtin("groups", _groups),
    })


def _encoding_module():
    import base64 as _b64
    import urllib.parse as _url

    def _b64_encode(a):
        return _b64.b64encode(a[0].encode("utf-8")).decode("ascii")

    def _b64_decode(a):
        try:
            return ok(_b64.b64decode(a[0]).decode("utf-8"))
        except Exception as e:
            return err(str(e))

    def _hex_encode(a):
        return a[0].encode("utf-8").hex()

    def _hex_decode(a):
        try:
            return ok(bytes.fromhex(a[0]).decode("utf-8"))
        except Exception as e:
            return err(str(e))

    return Module("encoding", {
        "base64_encode": Builtin("base64_encode", _b64_encode),
        "base64_decode": Builtin("base64_decode", _b64_decode),
        "hex_encode": Builtin("hex_encode", _hex_encode),
        "hex_decode": Builtin("hex_decode", _hex_decode),
        "url_encode": Builtin("url_encode", lambda a: _url.quote(a[0], safe="")),
        "url_decode": Builtin("url_decode", lambda a: _url.unquote(a[0])),
    })


def _crypto_module():
    import hashlib as _hl
    import hmac as _hmac

    return Module("crypto", {
        "md5": Builtin("md5", lambda a: _hl.md5(a[0].encode("utf-8")).hexdigest()),
        "sha1": Builtin("sha1", lambda a: _hl.sha1(a[0].encode("utf-8")).hexdigest()),
        "sha256": Builtin("sha256", lambda a: _hl.sha256(a[0].encode("utf-8")).hexdigest()),
        "sha512": Builtin("sha512", lambda a: _hl.sha512(a[0].encode("utf-8")).hexdigest()),
        "hmac_sha256": Builtin("hmac_sha256",
                               lambda a: _hmac.new(a[0].encode("utf-8"),
                                                   a[1].encode("utf-8"),
                                                   _hl.sha256).hexdigest()),
    })


def _compress_module():
    import zlib as _zlib
    import base64 as _b64

    def _compress(a):
        raw = _zlib.compress(a[0].encode("utf-8"), 9)
        return _b64.b64encode(raw).decode("ascii")

    def _decompress(a):
        try:
            raw = _b64.b64decode(a[0])
            return ok(_zlib.decompress(raw).decode("utf-8"))
        except Exception as e:
            return err(str(e))

    return Module("compress", {
        "compress": Builtin("compress", _compress),
        "decompress": Builtin("decompress", _decompress),
    })


def _os_module():
    import os as _os
    import subprocess as _sp

    def _getenv(a):
        v = _os.environ.get(a[0])
        return some(v) if v is not None else NONE

    def _run(a):
        # os.run(["cmd", "arg", ...]) -> Result[{code, stdout, stderr}, str]
        try:
            r = _sp.run(list(a[0]), capture_output=True, text=True)
            return ok(Struct("ProcessResult", {
                "code": r.returncode,
                "stdout": r.stdout,
                "stderr": r.stderr,
            }))
        except Exception as e:
            return err(str(e))

    def _args(a):
        import sys as _sys
        return list(_sys.argv[1:])

    return Module("os", {
        "getenv": Builtin("getenv", _getenv),
        "setenv": Builtin("setenv", lambda a: (_os.environ.__setitem__(a[0], a[1]), None)[1]),
        "cwd": Builtin("cwd", lambda a: _os.getcwd()),
        "listdir": Builtin("listdir", lambda a: _os_listdir(a[0])),
        "mkdir": Builtin("mkdir", lambda a: _os_mkdir(a[0])),
        "remove": Builtin("remove", lambda a: _os_remove(a[0])),
        "run": Builtin("run", _run),
        "args": Builtin("args", _args),
    })


def _os_listdir(path):
    import os as _os
    try:
        return ok(sorted(_os.listdir(path)))
    except OSError as e:
        return err(str(e))


def _os_mkdir(path):
    import os as _os
    try:
        _os.makedirs(path, exist_ok=True)
        return ok(None)
    except OSError as e:
        return err(str(e))


def _os_remove(path):
    import os as _os
    try:
        _os.remove(path)
        return ok(None)
    except OSError as e:
        return err(str(e))


def _log_module():
    import sys as _sys

    _levels = {"debug": 10, "info": 20, "warn": 30, "error": 40}
    _state = {"level": 20}

    def _emit(level, msg):
        if _levels[level] >= _state["level"]:
            _sys.stderr.write(f"[{level.upper()}] {ulang_str(msg)}\n")
        return None

    def _set_level(a):
        name = a[0]
        if name in _levels:
            _state["level"] = _levels[name]
        return None

    return Module("log", {
        "debug": Builtin("debug", lambda a: _emit("debug", a[0])),
        "info": Builtin("info", lambda a: _emit("info", a[0])),
        "warn": Builtin("warn", lambda a: _emit("warn", a[0])),
        "error": Builtin("error", lambda a: _emit("error", a[0])),
        "set_level": Builtin("set_level", _set_level),
    })


def _datetime_module():
    import datetime as _dt

    def _now(a):
        n = _dt.datetime.now()
        return _dt_struct(n)

    def _from_unix(a):
        n = _dt.datetime.fromtimestamp(a[0])
        return _dt_struct(n)

    def _format(a):
        # datetime.format(dt_struct, "YYYY-MM-DD HH:mm:ss")
        s = a[0]
        pat = a[1]
        rep = {
            "YYYY": f"{s.fields['year']:04d}",
            "MM": f"{s.fields['month']:02d}",
            "DD": f"{s.fields['day']:02d}",
            "HH": f"{s.fields['hour']:02d}",
            "mm": f"{s.fields['minute']:02d}",
            "ss": f"{s.fields['second']:02d}",
        }
        out = pat
        for k, v in rep.items():
            out = out.replace(k, v)
        return out

    return Module("datetime", {
        "now": Builtin("now", _now),
        "from_unix": Builtin("from_unix", _from_unix),
        "format": Builtin("format", _format),
    })


def _dt_struct(n):
    return Struct("DateTime", {
        "year": n.year, "month": n.month, "day": n.day,
        "hour": n.hour, "minute": n.minute, "second": n.second,
        "weekday": n.weekday(),
    })


def _platform_module():
    import platform_abi
    import tempfile
    host = platform_abi.HOST
    return Module("platform", {
        "os": host.os,
        "arch": host.arch,
        "exe_ext": host.exe_ext,
        "path_sep": host.path_sep,
        "line_sep": host.line_sep,
        "is_windows": Builtin("is_windows", lambda a: host.os == platform_abi.WINDOWS),
        "is_macos": Builtin("is_macos", lambda a: host.os == platform_abi.MACOS),
        "is_linux": Builtin("is_linux", lambda a: host.os == platform_abi.LINUX),
        "tmpdir": Builtin("tmpdir", lambda a: tempfile.gettempdir()),
    })


MODULES = {
    "fs": FS,
    "json": JSON,
    "math": MATH,
    "time": TIME,
    "str": STR,
    "random": RANDOM,
    "list": LIST,
}


def get_module(name):
    if name == "platform":
        return _platform_module()
    _lazy = {
        "regex": _regex_module,
        "encoding": _encoding_module,
        "crypto": _crypto_module,
        "compress": _compress_module,
        "os": _os_module,
        "log": _log_module,
        "datetime": _datetime_module,
    }
    if name in _lazy:
        return _lazy[name]()
    return MODULES.get(name)


# All standard-library module names (eager + lazily constructed), for tooling.
ALL_MODULE_NAMES = sorted(set(MODULES) | {
    "platform", "regex", "encoding", "crypto", "compress", "os", "log", "datetime",
})
