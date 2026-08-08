# -*- coding: utf-8 -*-
"""tally_batch 회귀 테스트.

**전부 2026-08-08에 실제로 당한 버그다.** 둘 다 예외를 내지 않고 조용히 틀린 답을 냈다.
집계 도구가 조용히 틀리면 그 위에 세운 판정이 전부 무효가 되므로 테스트로 못박는다.

  python -m pytest tools_diag/tests/test_tally_batch.py
  (pytest가 없으면)  python tools_diag/tests/test_tally_batch.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tally_batch as T  # noqa: E402


def _write(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


def test_negative_hp_is_parsed():
    """★ 버그1: 격추되면 tgtHP가 음수(-0.0025)가 되는데 정규식이 부호를 안 받아
    **격추된 판을 통째로 누락**했다. jink 15판 중 12판이 사라졌다."""
    log = _write(
        "########## v32 vs AIP_jink.dll ##########\n"
        "[seed 0] reward=   934.39 ownHP=1.0000 tgtHP=0.3935 max time out\n"
        "[seed 1] reward=   768.73 ownHP=1.0000 tgtHP=-0.0025 target destroyed\n"
        "[seed 2] reward=  1110.26 ownHP=-0.0070 tgtHP=1.0000 own destroyed\n"
    )
    rows = T.parse([log])[("v32", "AIP_jink.dll")]
    assert len(rows) == 3, f"격추된 판이 누락됐다: {len(rows)}/3"
    assert rows[1][3] == -0.0025
    assert rows[2][2] == -0.0070
    os.unlink(log)


def test_header_with_trailing_note():
    """★ 버그2: 헤더에 부가 문구가 붙으면 파싱이 끊겼다.
    `_rerule.log`의 6상대가 통째로 안 잡혀 기준선이 3상대로 나왔다."""
    log = _write(
        "########## v32 vs ACE (새 규칙) ##########\n"
        "[seed 0] reward=   259.93 ownHP=1.0000 tgtHP=0.9909 max time out\n"
    )
    got = T.parse([log])
    assert ("v32", "ACE") in got, f"부가 문구가 붙은 헤더를 못 읽는다: {list(got)}"
    os.unlink(log)


def test_summarize_uses_hp_comparison():
    """승패는 규정 제6조대로 HP 비교로 가른다(틱이 아니라)."""
    rows = [
        (0, 0.0, 1.0000, 0.9000),   # 승
        (1, 0.0, 0.8000, 1.0000),   # 패
        (2, 0.0, 1.0000, 1.0000),   # 무
    ]
    w, d, l, dealt, taken, net, _ = T.summarize(rows)
    assert (w, d, l) == (1, 1, 1)
    assert abs(dealt - 0.1) < 1e-9
    assert abs(taken - 0.2) < 1e-9
    assert abs(net - (-0.1)) < 1e-9


def test_max_seed_share_flags_variance():
    """★ 한 시드가 총합을 지배하면 그건 효과가 아니라 분산이다.
    실제로 onecircle이 112.5%(= 나머지가 순손해)로 나와 v21 제거를 막았다."""
    rows = [
        (0, 0.0, 1.0, 0.0),    # +1.0
        (1, 0.0, 0.9, 1.0),    # -0.1
    ]
    *_, net, top = T.summarize(rows)
    assert abs(net - 0.9) < 1e-9
    assert top > 100.0, f"최대기여시드 비중이 100%를 넘어야 한다: {top}"


def test_no_rows_gives_zero_share_not_crash():
    """빈 입력에서 죽지 않는다(0으로 나누기)."""
    assert T.summarize([]) == (0, 0, 0, 0.0, 0.0, 0.0, 0.0)


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
