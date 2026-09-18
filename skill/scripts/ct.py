#!/usr/bin/env python3
"""codetest 스킬의 단일 진입점.

상태는 전부 CT_HOME(기본 ~/COTE) 아래 평문 파일로 둔다. git 저장소이므로
집과 회사에서 pull/push 로 그대로 이어진다. 숨김 DB 를 쓰지 않는 이유는,
막혔을 때 사람이 직접 열어보고 고칠 수 있어야 하기 때문이다.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import judge as J  # noqa: E402

HOME = Path(os.environ.get("CT_HOME", Path.home() / "COTE"))
STATE = HOME / "state"
SESSIONS = HOME / "sessions"


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _latest():
    ds = [d for d in SESSIONS.glob("*") if d.is_dir()]
    if not ds:
        sys.exit("세션이 없다. 먼저 `ct.py new <이름> --tags ...` 로 만든다.")
    return max(ds, key=lambda d: d.stat().st_mtime)


def _sess(name):
    return _latest() if not name else (SESSIONS / name)


# ---------------------------------------------------------------- new

TESTS_STDIN = {"mode": "stdin", "cases": [{"in": "예제입력", "out": "예제출력"}]}
TESTS_FUNC = {"mode": "func", "func": "solution",
              "cases": [{"args": [[1, 2, 3]], "expect": 6}]}

SOL_STDIN = '''import sys
input = sys.stdin.readline


def main():
    pass


main()
'''

SOL_FUNC = '''def solution(arr):
    pass
'''


def cmd_new(a):
    slug = re.sub(r"[^\w가-힣-]+", "-", a.slug).strip("-")
    d = SESSIONS / f"{datetime.now():%Y-%m-%d_%H%M%S}_{slug}"
    d.mkdir(parents=True, exist_ok=True)
    func = a.mode == "func"
    (d / "problem.md").write_text(
        f"# {a.slug}\n\n<!-- 여기에 문제 지문을 붙여넣는다 -->\n", encoding="utf-8")
    (d / "solution.py").write_text(SOL_FUNC if func else SOL_STDIN, encoding="utf-8")
    _save(d / "tests.json", TESTS_FUNC if func else TESTS_STDIN)
    _save(d / "session.json", {
        "slug": slug, "tags": [t for t in a.tags.split(",") if t],
        "mode": a.mode, "started": datetime.now().isoformat(),
        "hints_used": 0, "result": None, "minutes": None,
    })
    print(f"세션 생성: {d}")
    print(f"  문제 지문 → {d/'problem.md'}")
    print(f"  풀이      → {d/'solution.py'}")
    print(f"  테스트    → {d/'tests.json'}")


# ---------------------------------------------------------------- judge

def cmd_judge(a):
    d = _sess(a.session)
    tests = _load(d / "tests.json", None)
    if not tests:
        sys.exit(f"tests.json 이 없다: {d}")
    res = J.judge(d / "solution.py", tests, timeout=a.timeout, mem_mb=a.mem)
    print(J.render(res))
    _save(d / "last_judge.json", res)
    sys.exit(0 if all(r["ok"] for r in res) else 1)


# ---------------------------------------------------------------- stress

def cmd_stress(a):
    """브루트포스와 랜덤 입력으로 대조해 반례를 찾는다.

    크기를 1부터 키워가며 찾기 때문에, 처음 걸리는 반례가 대개
    사람이 손으로 따라갈 수 있을 만큼 작다. 이게 핵심이다 —
    '틀렸습니다'만 알려주는 채점 사이트가 절대 못 해주는 일.
    """
    d = _sess(a.session)
    sol, brute, gen = d / "solution.py", d / "brute.py", d / "gen.py"
    for f in (brute, gen):
        if not f.exists():
            sys.exit(f"{f.name} 이 없다. 스트레스 테스트는 brute.py(느리지만 확실한 풀이)와 "
                     f"gen.py(랜덤 입력 생성기)가 있어야 한다.")
    mode = _load(d / "tests.json", {}).get("mode", "stdin")
    fn = _load(d / "tests.json", {}).get("func", "solution")
    tried = 0
    for size in range(1, a.max_size + 1):
        for seed in range(a.iters_per_size):
            tried += 1
            raw, err, _, st = J.run_raw(gen, "", a.timeout, a.mem, argv=[seed, size])
            if st != "ok":
                sys.exit(f"gen.py 실행 실패: {err[:300]}")
            if mode == "func":
                args = json.loads(raw)
                got, e1, _, s1 = J.run_func(sol, fn, args, a.timeout, a.mem)
                exp, e2, _, s2 = J.run_func(brute, fn, args, a.timeout, a.mem)
                shown = json.dumps(args, ensure_ascii=False)
                same = got == exp
            else:
                got, e1, _, s1 = J.run_raw(sol, raw, a.timeout, a.mem)
                exp, e2, _, s2 = J.run_raw(brute, raw, a.timeout, a.mem)
                shown = raw
                same = J._norm(got) == J._norm(exp)
            if s2 != "ok":
                sys.exit(f"brute.py 가 size={size} seed={seed} 에서 실패: {e2[:300]}")
            if s1 != "ok" or not same:
                print(f"\n🎯 반례 발견 (size={size}, seed={seed}, {tried}회 시도)\n")
                print(f"--- 입력 ---\n{str(shown)[:1500]}")
                print(f"\n--- 정답(brute) ---\n{str(exp)[:800]}")
                print(f"\n--- 내 풀이 ---\n{str(got)[:800]}")
                if s1 != "ok":
                    print(f"\n--- 상태: {s1} ---\n{e1[:500]}")
                _save(d / "counterexample.json",
                      {"input": shown, "expected": exp, "got": got, "status": s1})
                print(f"\n저장: {d/'counterexample.json'}")
                return
    print(f"✅ {tried}회 대조, 반례 없음. 로직은 맞을 가능성이 높다 "
          f"(단, 시간복잡도는 별개로 확인할 것).")


# ---------------------------------------------------------------- watch

def cmd_watch(a):
    """풀이 파일을 주기적으로 찍어 타임라인을 남긴다.

    푸는 동안에는 절대 개입하지 않는다. 실제 시험장에는 훈수 두는 사람이
    없고, 훈련 환경이 시험 환경과 달라지면 훈련의 의미가 없어지기 때문이다.
    기록은 다 푼 뒤 회고에만 쓴다.
    """
    d = _sess(a.session)
    sol, tl = d / "solution.py", d / "timeline.jsonl"
    t0, prev, last_change = time.time(), None, time.time()
    print(f"기록 시작: {sol}  (Ctrl+C 로 종료)")
    try:
        while True:
            try:
                cur = sol.read_text(encoding="utf-8")
            except FileNotFoundError:
                cur = ""
            if cur != prev:
                pl = len(prev or "")
                ev = {"t": round(time.time() - t0, 1), "chars": len(cur),
                      "lines": cur.count("\n") + 1, "delta": len(cur) - pl,
                      "idle_before": round(time.time() - last_change, 1)}
                if pl and len(cur) < pl * 0.7:
                    ev["event"] = "대량삭제"
                with tl.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
                prev, last_change = cur, time.time()
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print(f"\n기록 종료: {tl}")


def cmd_timeline(a):
    d = _sess(a.session)
    evs = [json.loads(l) for l in (d / "timeline.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()] if (d / "timeline.jsonl").exists() else []
    if not evs:
        sys.exit("타임라인이 없다. 풀기 전에 `ct.py watch` 를 백그라운드로 돌려야 한다.")
    print(f"총 {evs[-1]['t']/60:.1f}분, 편집 {len(evs)}회\n")
    for e in evs:
        mark = ""
        if e.get("event") == "대량삭제":
            mark = "  ⟵ 접근을 통째로 갈아엎음 (설계 단계에서 잡았어야 할 신호)"
        elif e["idle_before"] >= a.stall:
            mark = f"  ⟵ {e['idle_before']/60:.1f}분 정체"
        print(f"[{int(e['t'])//60:02d}:{int(e['t'])%60:02d}] {e['lines']:3d}줄 "
              f"({e['delta']:+d}자){mark}")
    stalls = [e for e in evs if e["idle_before"] >= a.stall]
    if stalls:
        tot = sum(e["idle_before"] for e in stalls) / 60
        print(f"\n정체 {len(stalls)}구간 / 합계 {tot:.1f}분. "
              f"여기가 다음 복습에서 다시 볼 지점이다.")


# ---------------------------------------------------------------- done / SRS

def sm2(card, q):
    """SuperMemo-2. 고정 간격표와 달리 '얼마나 쉬웠는지'가 다음 간격에 반영된다."""
    ef = card.get("ef", 2.5)
    ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    if q < 3:
        reps, iv = 0, 1
    else:
        reps = card.get("reps", 0) + 1
        iv = 1 if reps == 1 else 6 if reps == 2 else round(card.get("interval", 6) * ef)
    card.update(ef=round(ef, 2), reps=reps, interval=iv,
                due=(datetime.now() + timedelta(days=iv)).strftime("%Y-%m-%d"),
                last=datetime.now().strftime("%Y-%m-%d"))
    return card


def cmd_done(a):
    d = _sess(a.session)
    s = _load(d / "session.json", {})
    s.update(result=a.result, minutes=a.minutes, hints_used=a.hints,
             finished=datetime.now().isoformat())
    _save(d / "session.json", s)

    # 자기평가 점수를 SM-2 등급으로 환산한다. 힌트를 많이 봤거나 오래 걸렸으면
    # '기억해냈다'고 보기 어려우므로 등급을 깎는다.
    q = 5 if a.result == "solved" else 1
    q -= min(2, a.hints)
    if a.minutes and a.minutes > 40:
        q -= 1
    q = max(0, min(5, q))

    cards = _load(STATE / "srs.json", {})
    for tag in s.get("tags", []):
        cards[tag] = sm2(cards.get(tag, {"tag": tag}), q)
    _save(STATE / "srs.json", cards)

    weak = _load(STATE / "weak_tags.json", {})
    for tag in s.get("tags", []):
        w = weak.setdefault(tag, {"attempts": 0, "fails": 0})
        w["attempts"] += 1
        if a.result != "solved" or a.hints > 0:
            w["fails"] += 1
        w["rate"] = round(w["fails"] / w["attempts"], 2)
    _save(STATE / "weak_tags.json", weak)

    with (HOME / "progress.md").open("a", encoding="utf-8") as f:
        f.write(f"\n- {datetime.now():%Y-%m-%d %H:%M} `{s.get('slug')}` "
                f"[{','.join(s.get('tags', []))}] {a.result} "
                f"{a.minutes}분 힌트{a.hints} → SM2 q={q}\n")
    print(f"기록 완료. q={q}")
    for tag in s.get("tags", []):
        print(f"  {tag}: 다음 복습 {cards[tag]['due']} ({cards[tag]['interval']}일 뒤)")


def cmd_due(a):
    cards = _load(STATE / "srs.json", {})
    today = datetime.now().strftime("%Y-%m-%d")
    due = sorted([c for c in cards.values() if c.get("due", "9999") <= today],
                 key=lambda c: c.get("due", ""))
    if not due:
        print("오늘 복습할 유형 없음.")
        return
    print("오늘 복습할 유형:")
    for c in due:
        print(f"  - {c['tag']}  (마지막 {c.get('last','-')}, 간격 {c.get('interval')}일, EF {c.get('ef')})")


def cmd_status(a):
    weak = _load(STATE / "weak_tags.json", {})
    cards = _load(STATE / "srs.json", {})
    n = len(list(SESSIONS.glob("*"))) if SESSIONS.exists() else 0
    print(f"세션 {n}개 / 추적 유형 {len(weak)}개\n")
    if weak:
        print("약점 순위 (실패율 = 못 풀었거나 힌트를 본 비율):")
        for tag, w in sorted(weak.items(), key=lambda kv: -kv[1]["rate"]):
            bar = "█" * int(w["rate"] * 20)
            nxt = cards.get(tag, {}).get("due", "-")
            print(f"  {tag:14s} {w['rate']:.0%} {bar:<20s} {w['fails']}/{w['attempts']}  다음복습 {nxt}")
        top = max(weak.items(), key=lambda kv: kv[1]["rate"])[0]
        print(f"\n다음 문제는 '{top}' 유형에서 고르는 게 효율이 가장 높다.")


# ---------------------------------------------------------------- sync

def _git(*args, check=True):
    return subprocess.run(["git", "-C", str(HOME), *args],
                          capture_output=True, text=True, check=check)


def cmd_sync(a):
    """집↔회사 이어하기. 세션 시작 전과 끝난 뒤에 한 번씩 부른다."""
    if not (HOME / ".git").exists():
        sys.exit(f"{HOME} 이 git 저장소가 아니다. 먼저 clone 해야 한다.")
    if a.pull_only or a.direction == "pull":
        r = _git("pull", "--rebase", check=False)
        print(r.stdout or r.stderr)
        if r.returncode:
            sys.exit("pull 충돌. 양쪽에서 동시에 작업했을 수 있다. 직접 확인이 필요하다.")
        return
    _git("add", "-A")
    st = _git("status", "--porcelain").stdout.strip()
    if not st:
        print("변경 없음.")
    else:
        _git("commit", "-m", a.message or f"practice: {datetime.now():%Y-%m-%d %H:%M}")
        print(f"커밋: {len(st.splitlines())}개 파일")
    r = _git("push", check=False)
    print(r.stdout or r.stderr or "push 완료")
    if r.returncode:
        sys.exit("push 실패. `ct.py sync --direction pull` 로 먼저 당겨온다.")


# ---------------------------------------------------------------- cli

def main():
    p = argparse.ArgumentParser(prog="ct")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new"); n.add_argument("slug")
    n.add_argument("--tags", default=""); n.add_argument("--mode", default="stdin",
                                                         choices=["stdin", "func"])
    n.set_defaults(f=cmd_new)

    for name, fn in (("judge", cmd_judge),):
        c = sub.add_parser(name); c.add_argument("session", nargs="?")
        c.add_argument("--timeout", type=float, default=5.0)
        c.add_argument("--mem", type=int, default=512); c.set_defaults(f=fn)

    s = sub.add_parser("stress"); s.add_argument("session", nargs="?")
    s.add_argument("--iters-per-size", type=int, default=60)
    s.add_argument("--max-size", type=int, default=8)
    s.add_argument("--timeout", type=float, default=5.0)
    s.add_argument("--mem", type=int, default=512); s.set_defaults(f=cmd_stress)

    w = sub.add_parser("watch"); w.add_argument("session", nargs="?")
    w.add_argument("--interval", type=float, default=5.0); w.set_defaults(f=cmd_watch)

    t = sub.add_parser("timeline"); t.add_argument("session", nargs="?")
    t.add_argument("--stall", type=float, default=180); t.set_defaults(f=cmd_timeline)

    dn = sub.add_parser("done"); dn.add_argument("session", nargs="?")
    dn.add_argument("--result", required=True, choices=["solved", "gaveup"])
    dn.add_argument("--minutes", type=int, default=0)
    dn.add_argument("--hints", type=int, default=0); dn.set_defaults(f=cmd_done)

    sub.add_parser("due").set_defaults(f=cmd_due)
    sub.add_parser("status").set_defaults(f=cmd_status)

    sy = sub.add_parser("sync")
    sy.add_argument("--direction", default="push", choices=["push", "pull"])
    sy.add_argument("--pull-only", action="store_true")
    sy.add_argument("-m", "--message"); sy.set_defaults(f=cmd_sync)

    a = p.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    a.f(a)


if __name__ == "__main__":
    main()
