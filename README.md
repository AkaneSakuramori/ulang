# Mol

A compiled, statically-typed programming language with the readability of Python and
the performance of a native language. Mol aims to be a tier above interpreted languages:
fast native code, no GIL, safe by default, and easy to write.

> Status: **Step 1 of 10 — Spec & Grammar.** Early development.

## Why Mol

| Concern        | Python            | Mol (target)                          |
|----------------|-------------------|----------------------------------------|
| Speed          | Interpreted, slow | Native AOT via LLVM, C-class           |
| Concurrency    | GIL-bound         | Green threads, no GIL, true parallelism|
| Typing         | Optional hints    | Static + inferred, no null             |
| Errors         | Exceptions        | `Result` / `Option` values             |
| Deployment     | Interpreter + env | Single static binary                   |
| Feel           | Terse, readable   | Terse, readable                        |

## A taste

```mol
type User:
    id: int
    name: str
    email: str?
  derive(Display)

fn greet(u: User) -> str:
    match u.email:
        Some(e) => "${u.name} <${e}>"
        None    => u.name

fn main():
    let u = User(1, "ada", none)
    print(greet(u))
```

## Language highlights

- Python-style indentation, no semicolons or braces for blocks.
- Immutable by default (`let`), explicit mutability (`var`).
- Full local type inference — annotate only at boundaries.
- No null: `Option[T]` and `Result[T, E]` with the `?` propagation operator.
- Algebraic data types (`enum`) with exhaustive `match`.
- Traits for polymorphism, generics with bounds.
- First-class functions and closures, string interpolation.

## Repository layout

```
spec/        language specification and formal grammar
examples/    example .mol programs (the compiler's test corpus)
src/         compiler implementation (added from Step 2 onward)
tests/       compiler tests
```

- [`spec/SPEC.md`](spec/SPEC.md) — the v0 language specification.
- [`spec/grammar.ebnf`](spec/grammar.ebnf) — the formal EBNF grammar.
- [`examples/`](examples/) — 20 programs that define what Mol looks like and must compile.

## Roadmap

Mol is built in 10 shippable steps:

1. **Spec & Grammar** — language definition, EBNF, example programs. ← *current*
2. **Lexer** — source to tokens.
3. **Parser** — tokens to AST.
4. **Semantic analysis + type system** — inference and checking.
5. **Tree-walking interpreter** — the language first runs.
6. **Bytecode compiler + VM** — faster execution, REPL.
7. **Native backend (LLVM)** — single static binary, C-class speed.
8. **Runtime** — green-thread scheduler, structured concurrency, memory model.
9. **Stdlib + tooling + FFI** — http/web/json, `mol` CLI, LSP, package manager.
10. **Self-host + optimize + 1.0** — Mol compiles Mol, JIT tier, benchmarks.

## License

TBD.
