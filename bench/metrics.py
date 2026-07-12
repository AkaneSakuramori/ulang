"""Extended 2.0 benchmark suite: runtime, compiler, startup, and binary-size metrics.

Complements bench/benchmark.py (per-engine runtime) with the additional metrics the 2.0
milestone tracks: interpreter startup latency, native binary size, and self-hosted
compiler throughput. All numbers are indicative (single machine) and reproducible.
"""

import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ULANG = os.path.join(ROOT, "src", "ulang.py")


def _best(fn, n=5):
    times = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return min(times)


def startup_time():
    with tempfile.NamedTemporaryFile("w", suffix=".ul", delete=False) as f:
        f.write("fn main():\n    print(1)\n")
        path = f.name
    dt = _best(lambda: subprocess.run([sys.executable, ULANG, "run", path],
                                      capture_output=True))
    os.unlink(path)
    return dt * 1000  # ms


def native_binary_size():
    src = os.path.join(ROOT, "examples", "native", "fib.ul")
    out = tempfile.mktemp()
    r = subprocess.run([sys.executable, ULANG, "build", src, "-o", out],
                       capture_output=True, text=True)
    import platform_abi
    sys.path.insert(0, os.path.join(ROOT, "src"))
    exe = platform_abi.HOST.executable_name(out) if hasattr(platform_abi, "HOST") else out
    if not os.path.exists(exe):
        exe = out
    size = os.path.getsize(exe) if os.path.exists(exe) else 0
    if os.path.exists(exe):
        os.unlink(exe)
    return size


def selfhost_compile_time(project):
    path = os.path.join(ROOT, "projects", project)
    dt = _best(lambda: subprocess.run([sys.executable, ULANG, "selfhost", path],
                                      capture_output=True), n=3)
    return dt


def main():
    print("Ulang 2.0 metrics")
    print("=================")
    print(f"interpreter startup (run trivial program):  {startup_time():6.1f} ms")
    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        size = native_binary_size()
        print(f"native binary size (fib):                    {size:6d} bytes")
    except Exception as e:
        print(f"native binary size: unavailable ({e})")
    for proj in ("calc/calc.ul", "lisp/lisp.ul"):
        try:
            dt = selfhost_compile_time(proj)
            print(f"self-hosted compile ({proj:16s}):     {dt:6.2f} s")
        except Exception as e:
            print(f"self-hosted compile ({proj}): unavailable ({e})")
    print()
    print("Runtime engine benchmarks: run `python3 bench/benchmark.py`.")


if __name__ == "__main__":
    main()
