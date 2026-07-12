# Standard Library

The standard library ships with the toolchain. Modules are brought in with `import`.

## Built-in functions

Always available, no import needed:

| Function | Description |
|----------|-------------|
| `print(x)` | Print a value followed by a newline. |
| `len(x)` | Length of a string, list, dict, or tuple. |
| `range(a, b)` | List of integers from `a` up to (not including) `b`. |
| `panic(msg)` | Abort with a message. |
| `int(x)`, `float(x)`, `str(x)`, `bool(x)` | Conversions. |
| `abs(x)`, `min(...)`, `max(...)`, `sum(list)` | Numeric helpers. |
| `Some(x)`, `None`, `Ok(x)`, `Err(x)` | Option and Result constructors. |

## Methods

### List

`map(f)`, `filter(f)`, `reduce(f, init)`, `each(f)`, `len()`, `push(x)`, `pop()`,
`contains(x)`, `reverse()`, `sort()`, `first()`, `last()`, `join(sep)`.

```ulang
let squares = [1, 2, 3, 4].map(n => n * n)      # [1, 4, 9, 16]
let evens = [1, 2, 3, 4].filter(n => n % 2 == 0) # [2, 4]
let total = [1, 2, 3].reduce((a, b) => a + b, 0) # 6
```

`first()` and `last()` return an `Option`.

### String

`len()`, `upper()`, `lower()`, `split(sep)`, `trim()`, `replace(a, b)`, `contains(s)`,
`starts_with(s)`, `ends_with(s)`, `chars()`.

```ulang
let parts = "a,b,c".split(",")   # ["a", "b", "c"]
print("Hello".lower())           # hello
```

### Dict

`len()`, `keys()`, `values()`, `get(k)`, `has(k)`, `set(k, v)`, `remove(k)`.

```ulang
let scores = {"ada": 90}
print(scores.keys())        # ["ada"]
print(scores.get("bob"))    # None
```

`get(k)` returns an `Option`.

### Option and Result

`is_some()`, `is_none()`, `is_ok()`, `is_err()`, `unwrap()`, `unwrap_or(default)`.

```ulang
let x = Some(5)
print(x.unwrap_or(0))   # 5
print(None.unwrap_or(0)) # 0
```

## Modules

### `fs` — filesystem

| Function | Returns |
|----------|---------|
| `fs.read(path)` | `Result[str, str]` |
| `fs.write(path, data)` | `Result[none, str]` |
| `fs.open(path)` | file handle with `.write`, `.read`, `.close` |
| `fs.exists(path)` | `bool` |

### `json`

| Function | Description |
|----------|-------------|
| `json.dumps(value)` | Serialize to a JSON string. |
| `json.loads(text)` | Parse a JSON string. |

### `math`

`math.sqrt(x)`, `math.pow(x, y)`, `math.floor(x)`, `math.ceil(x)`, `math.abs(x)`,
`math.sin(x)`, `math.cos(x)`, `math.tan(x)`, `math.log(x[, base])`, `math.exp(x)`,
`math.min(a, b)`, `math.max(a, b)`, `math.round(x)`, and the constants `math.pi`, `math.e`.

### `time`

`time.now()` (seconds), `time.now_ms()` (milliseconds), `time.sleep(ms)`.

### `str`

`str.from_int(n)`, `str.to_int(s)` (returns `Result`), `str.repeat(s, n)`,
`str.join(sep, list)`.

### `random`

`random.int(lo, hi)`, `random.float()`, `random.choice(list)`, `random.seed(n)`.

### `list`

`list.range(a, b)`, `list.repeat(x, n)`, `list.concat(a, b)`.

### `os` — environment and processes

| Function | Returns |
|----------|---------|
| `os.getenv(name)` | `Option[str]` |
| `os.setenv(name, value)` | `none` |
| `os.cwd()` | `str` — current working directory |
| `os.listdir(path)` | `Result[[str], str]` |
| `os.mkdir(path)` | `Result[none, str]` (creates parents) |
| `os.remove(path)` | `Result[none, str]` |
| `os.run(argv)` | `Result[ProcessResult, str]` — `.code`, `.stdout`, `.stderr` |
| `os.args()` | `[str]` — command-line arguments |

### `regex` — regular expressions

| Function | Returns |
|----------|---------|
| `regex.test(pattern, text)` | `bool` — does the pattern occur? |
| `regex.match(pattern, text)` | `bool` — does the pattern match the whole string? |
| `regex.search(pattern, text)` | `Option[str]` — first match |
| `regex.find_all(pattern, text)` | `[str]` |
| `regex.replace(pattern, replacement, text)` | `str` |
| `regex.split(pattern, text)` | `[str]` |
| `regex.groups(pattern, text)` | `Option[[str]]` — captured groups |

### `encoding` — text encodings

`encoding.base64_encode(s)` / `encoding.base64_decode(s)` (returns `Result`),
`encoding.hex_encode(s)` / `encoding.hex_decode(s)` (returns `Result`),
`encoding.url_encode(s)` / `encoding.url_decode(s)`.

### `crypto` — hashing

`crypto.md5(s)`, `crypto.sha1(s)`, `crypto.sha256(s)`, `crypto.sha512(s)` (all return a
hex digest), and `crypto.hmac_sha256(key, message)`.

### `compress` — compression

`compress.compress(s)` returns a base64-wrapped zlib payload; `compress.decompress(s)`
returns `Result[str, str]`.

### `datetime` — dates and times

`datetime.now()` and `datetime.from_unix(seconds)` return a `DateTime` (`.year`, `.month`,
`.day`, `.hour`, `.minute`, `.second`, `.weekday`). `datetime.format(dt, pattern)` supports
`YYYY`, `MM`, `DD`, `HH`, `mm`, `ss`.

### `log` — leveled logging

`log.debug(msg)`, `log.info(msg)`, `log.warn(msg)`, `log.error(msg)` write to standard
error; `log.set_level("debug"|"info"|"warn"|"error")` sets the threshold.

### `platform` — host introspection

`platform.os`, `platform.arch`, `platform.exe_ext`, `platform.is_windows()`,
`platform.is_macos()`, `platform.is_linux()`, and `platform.tmpdir()`.

## Example

```ulang
import math
import json

type Point:
    x: int
    y: int
derive(Serialize)

fn main():
    print(math.sqrt(144.0))       # 12.0
    let p = Point(3, 4)
    print(json.dumps(p))          # {"x": 3, "y": 4}
```
