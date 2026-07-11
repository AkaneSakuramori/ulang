# The Ulang Compiler, in Ulang

This directory holds the self-hosted Ulang compiler — the compiler for Ulang, written in
Ulang itself. It is being built incrementally, one compiler stage at a time, and each
stage is validated for identical behavior against the Python reference implementation in
`src/` before the next begins.

## Layout

Files are named by compiler responsibility, not by development milestone:

```
compiler/
  lexer.ul       source text  -> token stream (with significant-indentation layout)
  parser.ul      token stream -> syntax tree
  checker.ul     syntax tree  -> semantic diagnostics (name resolution + type checking)
  exports.ul     syntax tree  -> a module's public API (visibility / package exports)
  consteval.ul   syntax tree  -> compile-time values of constant expressions
  optimizer.ul   syntax tree  -> optimized syntax tree (behavior-preserving passes)
```

## Status

- **Stage 1 — Parsing: complete.** `lexer.ul` and `parser.ul` together parse every
  language construct the reference compiler supports, verified identical to the reference
  (`tests/test_selfhost_lexer.py`, `tests/test_selfhost_parser.py`).
- **Stage 2 — Semantic analysis: complete.** Every semantic rule the reference performs is
  reproduced in Ulang and verified equivalent:
  - Name resolution and type checking, pattern validation, and exhaustiveness (`checker.ul`).
  - Visibility / package exports (`exports.ul`).
  - Constant evaluation (`consteval.ul`).
- **Stage 3 — Optimization and code generation: in progress.**
  - AST optimizer (`optimizer.ul`): the behavior-preserving passes of the reference
    `src/optimizer.py` — constant folding, constant propagation through immutable
    `let`/`const` bindings, dead-branch elimination (`if`/`elif`/`else`, `while false`,
    ternaries), and algebraic identities (`x + 0`, `x * 1`) — producing an optimized syntax
    tree byte-identical to the reference (`tests/test_selfhost_optimizer.py`).

## Note on literals

The self-hosted pipeline exchanges a canonical syntax-tree form in which string and float
literals are opaque atoms (`(str)`, `(flt)`); integer and boolean literals carry their
values. Every optimizer pass over integer, boolean, and structural forms is therefore
reproduced exactly. Constant folding of string/float *values* (for example `"a" + "b"` or
`1.5 + 2.5`) is a property of the reference's literal-preserving AST that is intentionally
outside this representation; it is covered by the reference's own optimizer tests and does
not affect program behavior.

## Running

```sh
cp path/to/program.ul input.ul
ulang run selfhost/compiler/lexer.ul       # token stream
ulang run selfhost/compiler/parser.ul > tree.sexpr
ulang run selfhost/compiler/checker.ul     # semantic diagnostics
ulang run selfhost/compiler/exports.ul     # public API
ulang run selfhost/compiler/consteval.ul   # constant values
ulang run selfhost/compiler/optimizer.ul   # optimized syntax tree
```

## Validation approach

The self-hosted components emit a canonical, textual form of their output (token streams
and S-expression syntax trees). The Python reference emits the same canonical form via
`src/ast_serialize.py`. The conformance tests compare the two exactly, so any divergence
in behavior is caught immediately.
