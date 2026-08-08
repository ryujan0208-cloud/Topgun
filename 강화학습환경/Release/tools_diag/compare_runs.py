# -*- coding: utf-8 -*-
"""같은 로그 안의 두 실행이 **시드별로 완전히 같은지** 판정한다.

[왜 필요한가]
계측이나 게이트를 넣은 DLL이 "무동작"인지 확인할 때, 집계값(SUMMARY)이 같은 것만으로는
부족하다. 서로 다른 판이 상쇄돼 합계만 같을 수 있다. 시드별로 전부 같아야 한다.
(코덱스가 CV01에서 계측 DLL의 정상 경로를 트랙 해시로 검증한 것과 같은 취지)

사용: python tools_diag/compare_runs.py <로그> [실행쌍 ...]
      실행쌍을 안 주면 (0,1) (2,3) ... 순서로 짝짓는다.
"""
import re
import sys

HDR = re.compile(r"^#{5,}\s*(\S+)\s+vs\s+(\S+)[^#]*#{5,}")
SEED = re.compile(
    r"^\[seed\s+(\d+)\]\s+reward=\s*(-?[\d.]+)\s+ownHP=(-?[\d.]+)\s+tgtHP=(-?[\d.]+)"
)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    runs = []          # [(라벨, 상대), [시드라인, ...]]
    cur = None
    with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            m = HDR.match(s)
            if m:
                cur = (m.group(1), m.group(2))
                runs.append([cur, []])
                continue
            if cur is None:
                continue
            m = SEED.match(s)
            if m:
                # 종료사유는 문자열 변동 여지가 있어 수치 4개만 비교한다
                runs[-1][1].append(m.groups())

    print(f"실행 {len(runs)}개")
    for i, ((lab, opp), rows) in enumerate(runs):
        print(f"  [{i}] {lab:>10} vs {opp:<20} 시드 {len(rows)}")

    pairs = [(i, i + 1) for i in range(0, len(runs) - 1, 2)]
    print()
    allok = True
    for a, b in pairs:
        (la, oa), ra = runs[a]
        (lb, ob), rb = runs[b]
        same = (ra == rb) and len(ra) > 0
        allok &= same
        mark = "완전 일치" if same else "★ 불일치"
        print(f"[{oa}] {la} vs {lb} — 시드 {len(ra)}/{len(rb)} -> {mark}")
        if not same:
            for k, (x, y) in enumerate(zip(ra, rb)):
                if x != y:
                    print(f"    seed {k}")
                    print(f"      {la:>8}: reward={x[1]} ownHP={x[2]} tgtHP={x[3]}")
                    print(f"      {lb:>8}: reward={y[1]} ownHP={y[2]} tgtHP={y[3]}")
            if len(ra) != len(rb):
                print(f"    시드 개수가 다르다: {len(ra)} vs {len(rb)}")

    print()
    print("=" * 62)
    if allok:
        print("판정: 통과 — 두 실행이 시드별로 동일하다.")
        return 0
    print("판정: 실패 — 동일하지 않다. 이 상태의 측정은 신뢰할 수 없다.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
