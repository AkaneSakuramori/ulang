# Package Management

Ulang includes a package manager for discovering, installing, updating, publishing, and
removing libraries. It is designed for reproducible builds and verified, tamper-evident
downloads.

## Concepts

- **Package** — a directory with a `ulang.toml` manifest and `.ul` sources under `src/`.
- **Registry** — where published packages live. Each release is stored as an artifact
  with a SHA-256 checksum. The default registry is `~/.ulang/registry`; override it with
  the `ULANG_REGISTRY` environment variable.
- **Manifest (`ulang.toml`)** — declares your package and its dependencies.
- **Lockfile (`ulang.lock`)** — records the exact resolved versions and checksums so an
  install is byte-for-byte reproducible.
- **`ulang_modules/`** — where resolved dependencies are installed for a project.

## The manifest

```toml
[package]
name = "myapp"
version = "0.1.0"
description = "an example application"
entry = "src/main.ul"
license = "MIT"

[dependencies]
greeter = "^1.2.0"
json_ext = "~0.3.1"
```

Package names are lowercase and may contain letters, digits, `-`, and `_`. Versions are
semantic versions (`major.minor.patch`, with an optional `-prerelease`).

## Version constraints

| Constraint | Meaning |
|------------|---------|
| `^1.2.3` | `>=1.2.3` and `<2.0.0` (compatible releases) |
| `~1.2.3` | `>=1.2.3` and `<1.3.0` (patch-level) |
| `>=1.2.0` | at least `1.2.0` |
| `<2.0.0` | below `2.0.0` |
| `=1.2.3` | exactly `1.2.3` |
| `*` | any version |

`^0.x` treats the minor version as breaking, matching common ecosystem conventions:
`^0.2.3` allows `<0.3.0`.

## Commands

### Start a project

```sh
ulang init myapp
```

Creates `ulang.toml` and `src/main.ul`.

### Add a dependency

```sh
ulang add greeter            # latest, recorded as ^version
ulang add greeter ^1.2.0     # explicit constraint
```

This updates the manifest, re-resolves, writes `ulang.lock`, and installs.

### Install from the manifest and lockfile

```sh
ulang install
```

If a lockfile exists and satisfies the manifest, it is used as-is (reproducible). If not,
dependencies are resolved and a new lockfile is written. Every artifact is verified
against its checksum before extraction.

### Update to the newest allowed versions

```sh
ulang update
```

Discards the lockfile and re-resolves within your constraints, then reinstalls.

### Remove a dependency

```sh
ulang remove greeter
```

Removes it from the manifest and prunes it — and any newly-orphaned transitive
dependencies — from `ulang_modules/`.

### List what is installed

```sh
ulang list
```

### Search the registry

```sh
ulang search json
```

### Publish

```sh
ulang publish
```

Packages the current project's manifest and `src/*.ul`, computes a checksum, and records
a new immutable release in the registry. Re-publishing an existing version is rejected.

## Using a dependency

Once installed, import a package by name:

```ulang
import greeter

fn main():
    print(greeter.hi("world"))
```

The loader looks in `ulang_modules/` and exposes the package's `pub` functions, types,
and enums as members of the imported module. A library marks its public API with `pub`:

```ulang
pub fn hi(name: str) -> str:
    return "hi ${name}"
```

## Dependency resolution

The resolver picks the highest version of each package that satisfies **all** constraints
across the dependency graph, unifying shared dependencies to a single version. When no
version can satisfy every constraint, it reports which requirements conflict instead of
guessing.

## Reproducible builds

The lockfile pins the exact version and SHA-256 checksum of every package in the graph.
Committing `ulang.lock` means every machine installs identical bytes. During install, a
mismatch between the lockfile checksum and the artifact aborts the operation.

## Security

- **Content integrity.** Every artifact has a SHA-256 checksum stored in the registry
  index and the lockfile. Downloads are verified before use; tampering is detected.
- **Immutable releases.** A published version cannot be overwritten.
- **Safe extraction.** Archive paths are validated; absolute paths and `..` traversal are
  rejected.

## Files to commit

Commit `ulang.toml` and `ulang.lock`. Do not commit `ulang_modules/` — it is regenerated
by `ulang install`.
