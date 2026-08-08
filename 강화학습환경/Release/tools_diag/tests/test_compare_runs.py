# -*- coding: utf-8 -*-
"""compare_runs 회귀 테스트.

이 도구는 "계측/게이트를 붙여도 동작이 안 변했다"를 증명하는 데 쓴다.
**틀리면 그 위의 모든 실험이 무효**가 되므로 특히 조심해야 한다.

  python tools_diag/tests/test_compare_runs.py
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "compare_runs.py")
PY = sys.executable


def _run(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    p = subprocess.run([PY, TOOL, f.name], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    os.unlink(f.name)
    return p.returncode, (p.stdout or "")


HDR_A = "########## v32 vs AIP_v7.dll ##########\n"
HDR_B = "########## dtfix vs AIP_v7.dll ##########\n"
S = "[seed {i}] reward=   {r} ownHP=1.0000 tgtHP={t} max time out\n"


def test_identical_runs_pass():
    body = "".join(S.format(i=i, r=100 + i, t=0.9) for i in range(3))
    code, out = _run(HDR_A + body + HDR_B + body)
    assert "완전 일치" in out, out
    assert code == 0, f"동일한데 통과가 아니다: {code}\n{out}"


def test_differing_runs_fail():
    a = "".join(S.format(i=i, r=100 + i, t=0.9) for i in range(3))
    b = "".join(S.format(i=i, r=100 + i, t=0.9 if i != 1 else 0.5) for i in range(3))
    code, out = _run(HDR_A + a + HDR_B + b)
    assert "불일치" in out, out
    assert code != 0, "달라졌는데 통과로 보고했다"


def test_empty_log_is_undecidable_not_pass():
    """★ 2026-08-08 실제 사고: 배치가 아직 도는 중인 로그를 읽었더니
    비교할 쌍이 0개인데 **'통과'라고 보고**했다.
    검증 도구가 데이터 부족을 통과로 만드는 것이 가장 위험한 오류다."""
    code, out = _run(HDR_A)          # 헤더만, 시드 0개
    assert "통과" not in out, f"데이터가 없는데 통과라고 했다:\n{out}"
    assert code != 0, f"데이터가 없는데 성공 코드를 냈다: {code}"


def test_header_only_pair_is_not_match():
    """양쪽 다 시드 0개여도 '일치'가 아니다 — 잰 게 없다."""
    code, out = _run(HDR_A + HDR_B)
    assert "완전 일치" not in out, out
    assert code != 0


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except AssertionError as e:
                fails += 1
                print(f"  FAIL  {name}: {e}")
    print("실패" if fails else "전부 통과")
    sys.exit(1 if fails else 0)
