# Bootstrapping the Ulang Compiler

Ulang has a **self-hosted compiler** — the compiler for Ulang, written in Ulang — living
in [`selfhost/compiler/`](../selfhost/compiler/). This document describes how it is built
and validated, and states precisely what is and is not yet independent of the reference
implementation.

## The pipeline

The self-hosted compiler is a classic staged pipeline. Each stage is a program written in
Ulang; together they take a source file to its final compiled output:

```
source
  → lexer.ul       tokens (with INDENT/DEDENT/NEWLINE layout)
  → parser.ul      syntax tree (S-expressions)
  → checker.ul     semantic diagnostics (names, types, patterns, exhaustiveness)
  → exports.ul     the module's public API
  → consteval.ul   compile-time constant values
  → optimizer.ul   optimized syntax tree
  → bytecode.ul    stack-VM bytecode      (VM target)
  → codegen.ul     LLVM IR                (native target, numeric/control-flow core)
```

The stages exchange a single canonical form — the S-expression syntax tree — so the
pipeline composes cleanly. The integrated entry point is:

```sh
ulang selfhost path/to/program.ul            # compile to bytecode via the self-hosted compiler
ulang selfhost path/to/program.ul --native   # compile to native LLVM IR
```

`ulang selfhost` runs the whole self-hosted pipeline: it parses, type-checks (stopping with
diagnostics if the program is invalid), optimizes, and emits the final output.

## The bootstrap process

The bootstrap follows the standard two-stage pattern:

1. **Stage 0 — the reference compiler.** The Python implementation in [`src/`](../src/) is
   the reference specification. It also serves as the *host* that runs Ulang programs
   (the interpreter / VM / native backend).

2. **Stage 1 — the Ulang compiler, run on the host.** The self-hosted compiler
   (`selfhost/compiler/*.ul`) is executed on the Stage-0 runtime and used to compile Ulang
   source — including its own source.

`tests/test_bootstrap.py` validates the bootstrap end to end. It checks two properties,
treating the Python compiler as the reference specification:

- **Equivalence.** For every stage — tokens, syntax tree, diagnostics, exports, optimized
  tree, and bytecode — the self-hosted compiler's output is identical to the reference
  across the example programs.
- **Self-compilation.** The self-hosted compiler compiles its *own* source files through
  the front and middle end (lex, parse, type-check, optimize), and the results agree with
  the reference. This is the "the Ulang compiler processes itself" step.

Run it with:

```sh
python3 tests/test_bootstrap.py
```

## What is self-hosted today

- The **entire compiler front end and middle end** — lexer, parser, type checker,
  visibility/exports, constant evaluation, and the optimizer — is written in Ulang and
  proven equivalent to the reference, including on the compiler's own source.
- **Bytecode generation** is written in Ulang and proven instruction-for-instruction
  identical to the reference.
- **Native code generation** for the numeric and control-flow core is written in Ulang and
  produces binaries whose output matches the reference.

## What still depends on the reference implementation, and why

Two honest limitations remain. Neither affects the correctness of compiled programs; both
are inherent to the current architecture and define the road beyond this release.

1. **The runtime host is still Python.** A `.ul` program — including each self-hosted
   compiler stage — is *executed* by the Ulang runtime, which today is the Python
   interpreter/VM. Running the Ulang compiler therefore still requires the Python host. To
   remove it, the Ulang compiler must be compiled to a **standalone native binary**, which
   requires the native backend to support the *entire* language (heap types — strings,
   lists, dicts, structs, closures — plus the garbage collector). The self-hosted native
   backend today covers only the numeric/control-flow core, so the compiler (which is heavy
   on strings, lists, and structs) cannot yet be compiled to a native executable by either
   backend.

2. **String interpolation is opaque in the canonical tree.** The self-hosted pipeline
   exchanges a syntax-tree form in which string and float literals are opaque atoms
   (`(str)`, `(flt)`); integer and boolean literals carry their values. Every pass over
   integer/boolean/structural forms is reproduced exactly. Behaviors that depend on a
   literal's *value* — string interpolation's embedded sub-expressions, and constant
   folding of string/float values — fall outside this representation. They are covered by
   the reference's own tests and do not change program behavior.

### The path to a fully independent (Python-free) toolchain

A toolchain with no Python dependency requires, in order:

1. A **literal-preserving canonical tree** so the self-hosted compiler carries string and
   float values (closing boundary 2 and enabling full-fidelity codegen for those forms).
2. A **full native backend** in Ulang covering heap types, closures, and the GC, so the
   compiler can be compiled to a native binary.
3. A **native GC runtime and entry runtime** the compiled compiler links against (the
   C runtime in [`runtime/`](../runtime/) already exists for this purpose).

With those, the Python host can compile the Ulang compiler once to a native binary, after
which the binary compiles itself and all Ulang programs with no Python involved. That is
the objective beyond the current series.

## Reproducibility

The bootstrap is deterministic: the self-hosted stages are pure functions of their input
(no clocks, no randomness), so re-running the pipeline on the same source produces
byte-identical output. `tests/test_bootstrap.py` runs in CI on every platform.
