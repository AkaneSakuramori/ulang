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
  bytecode.ul    syntax tree  -> stack-VM bytecode (with peephole)
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
  - Bytecode generation (`bytecode.ul`): compiles the syntax tree to stack-VM bytecode,
    mirroring the reference `src/compiler.py` — expressions, control flow, loops with
    `break`/`continue`, pattern-matching dispatch, tail-position block values, nested
    closures, and the same peephole pass (jump-to-next and unreachable-code removal with
    jump-target remapping). Verified instruction-for-instruction identical to the reference
    (`tests/test_selfhost_bytecode.py`).

## Note on literals

The self-hosted pipeline exchanges a canonical syntax-tree form in which string and float
literals are opaque atoms (`(str)`, `(flt)`); integer and boolean literals carry their
values. Every pass over integer, boolean, and structural forms is therefore reproduced
exactly. Two behaviors depend on literal *values* that this representation intentionally
omits, are covered by the reference's own tests, and do not affect program behavior:
constant folding of string/float values (e.g. `"a" + "b"`, `1.5 + 2.5`), and the bytecode
for string *interpolation* (whose embedded sub-expressions are not carried by an opaque
string atom). Constant strings and floats compile to identical (opaque) bytecode.

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
