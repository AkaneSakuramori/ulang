# Ulang benchmarks

Indicative performance numbers, reproducible with the scripts in `bench/`. All figures are
from a single Linux machine; treat them as relative, not absolute.

## Runtime engines

`python3 bench/benchmark.py` runs each workload on all four execution engines — the
tree-walking interpreter, the bytecode VM, the tiered JIT, and the native (LLVM) backend —
and verifies they produce identical output.

| workload | interpreter | VM | JIT | native |
|---|---|---|---|---|
| `fib(30)` | 19.8 s | 13.4 s | 16.1 ms | 5.4 ms |
| `count_primes(20000)` | 2.04 s | 1.84 s | 91.4 ms | 2.5 ms |
| `loop_sum(3000000)` | 5.47 s | 9.29 s | 5.73 s | 2.8 ms |

The JIT and native backends are several orders of magnitude faster than the interpreter on
compute-bound code; the native backend turns `fib(30)` into a ~5 ms binary. All four
engines produce byte-identical output for every workload.

## Toolchain metrics

`python3 bench/metrics.py` captures the additional metrics tracked for 2.0:

| metric | value |
|---|---|
| interpreter startup (run a trivial program) | ~45 ms |
| native binary size (`fib`) | ~16.7 KB |
| self-hosted compile of `calc` (27 functions) | ~2.8 s |
| self-hosted compile of `lisp` (33 functions) | ~4.2 s |

The self-hosted compile time reflects the current bootstrap architecture: `ulang selfhost`
runs each compiler stage as a separate process on the Python runtime host and passes the
canonical syntax tree between them (see [bootstrapping.md](bootstrapping.md)). It is a
correctness-first integration, not yet a throughput-optimized one — improving it is part of
the work toward a native, self-hosting toolchain.

## Memory

`python3 bench/memory_benchmark.py` reports allocation and garbage-collection behaviour for
the managed engines.
