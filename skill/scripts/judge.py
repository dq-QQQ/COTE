#!/usr/bin/env python3
"""코드를 제한된 서브프로세스로 실행하고 채점한다.

두 가지 입출력 모드를 지원한다:
  stdin — 표준입력/출력 (백준·SWEA 형식)
  func  — solution(...) 함수 호출 (프로그래머스·리트코드 형식)

단독 실행도 가능하지만 보통 ct.py 가 import 해서 쓴다.
"""

import json
import os
import resource
import subprocess
import sys
import tempfile
import time

DEFAULT_TIMEOUT = 5.0
DEFAULT_MEM_MB = 512


def _limiter(mem_mb: int, cpu_s: int):
    """자식 프로세스에만 자원 상한을 건다. 무한루프·메모리 폭주가
    에디터나 셸을 끌어내리지 않게 하는 것이 목적이다."""
    def apply():
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        except (ValueError, OSError):
            pass
        try:
            b = mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (b, b))
        except (ValueError, OSError):
            pass
    return apply


def run_raw(path, stdin_text="", timeout=DEFAULT_TIMEOUT, mem_mb=DEFAULT_MEM_MB, argv=None):
    """파이썬 파일 하나를 실행하고 (stdout, stderr, 경과초, 상태) 를 돌려준다.

    상태는 ok / timeout / runtime_error / memory 중 하나.
    """
    cmd = [sys.executable, str(path)] + [str(a) for a in (argv or [])]
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=_limiter(mem_mb, int(timeout) + 1),
            env={**os.environ, "PYTHONHASHSEED": "0"},
        )
    except subprocess.TimeoutExpired:
        return "", f"{timeout}초 초과", time.perf_counter() - t0, "timeout"
    el = time.perf_counter() - t0
    if p.returncode != 0:
        err = p.stderr.strip()
        status = "memory" if "MemoryError" in err else "runtime_error"
        return p.stdout, err, el, status
    return p.stdout, p.stderr, el, "ok"


_FUNC_DRIVER = """
import json, sys, importlib.util
spec = importlib.util.spec_from_file_location("sol", {sol!r})
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
args = json.loads(sys.stdin.read())
print(json.dumps(getattr(m, {fn!r})(*args), ensure_ascii=False, default=str))
"""


def run_func(sol_path, fn, args, timeout=DEFAULT_TIMEOUT, mem_mb=DEFAULT_MEM_MB):
    """solution(...) 형태의 함수를 호출하고 반환값을 JSON 으로 받는다."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(_FUNC_DRIVER.format(sol=str(sol_path), fn=fn))
        drv = f.name
    try:
        out, err, el, st = run_raw(drv, json.dumps(args, ensure_ascii=False), timeout, mem_mb)
    finally:
        os.unlink(drv)
    if st != "ok":
        return None, err, el, st
    try:
        return json.loads(out.strip()), err, el, "ok"
    except json.JSONDecodeError:
        return out.strip(), err, el, "ok"


def _norm(s):
    """줄 끝 공백과 마지막 개행 차이로 오답 처리되는 일을 막는다."""
    return "\n".join(line.rstrip() for line in str(s).strip().splitlines())


def judge(sol_path, tests, timeout=DEFAULT_TIMEOUT, mem_mb=DEFAULT_MEM_MB):
    """tests.json 의 케이스를 모두 돌리고 케이스별 결과 리스트를 돌려준다."""
    mode = tests.get("mode", "stdin")
    fn = tests.get("func", "solution")
    results = []
    for i, c in enumerate(tests.get("cases", [])):
        if mode == "func":
            got, err, el, st = run_func(sol_path, fn, c["args"], timeout, mem_mb)
            want = c.get("expect")
            ok = (st == "ok") and got == want
            shown_in = json.dumps(c["args"], ensure_ascii=False)
        else:
            got, err, el, st = run_raw(sol_path, c["in"], timeout, mem_mb)
            want = c.get("out", "")
            ok = (st == "ok") and _norm(got) == _norm(want)
            shown_in = c["in"]
        results.append({
            "case": i + 1, "ok": ok, "status": st, "elapsed": round(el, 3),
            "input": shown_in, "expected": want, "got": got, "stderr": (err or "")[:600],
        })
    return results


def render(results):
    """사람이 읽을 채점표. 틀린 케이스는 입력·기대·실제를 같이 보여준다."""
    lines, passed = [], 0
    for r in results:
        if r["ok"]:
            passed += 1
            lines.append(f"  ✅ #{r['case']}  {r['elapsed']}s")
        else:
            tag = {"timeout": "⏱  시간초과", "runtime_error": "💥 런타임에러",
                   "memory": "🧠 메모리초과"}.get(r["status"], "❌ 오답")
            lines.append(f"  {tag} #{r['case']}  {r['elapsed']}s")
            lines.append(f"      입력: {str(r['input'])[:200]}")
            lines.append(f"      기대: {str(r['expected'])[:200]}")
            lines.append(f"      실제: {str(r['got'])[:200]}")
            if r["stderr"]:
                lines.append(f"      stderr: {r['stderr'].splitlines()[-1][:200]}")
    head = f"{passed}/{len(results)} 통과"
    return head + "\n" + "\n".join(lines)


if __name__ == "__main__":
    sol, tj = sys.argv[1], sys.argv[2]
    res = judge(sol, json.load(open(tj, encoding="utf-8")))
    print(render(res))
    sys.exit(0 if all(r["ok"] for r in res) else 1)
