# -*- coding: utf-8 -*-
"""배치 로그에서 상대별 승/무/패·순이득을 집계한다.

판정은 규정 제6조: 200초 타임아웃 시 HP 비교.
  승 = ownHP > tgtHP,  패 = ownHP < tgtHP,  무 = 같음
조기종료(격추/고도이탈)도 같은 부등호로 갈린다.

읽기 전용. 배치가 도는 중에도 안전하다.

  python tools_diag/tally_batch.py _v39c.log _v39b.log _v39.log
"""
import re
import sys
from collections import OrderedDict

# 상대 이름 뒤에 부가 문구가 붙는 로그가 있다: "########## v32 vs ACE (새 규칙) ##########"
HDR = re.compile(r"^#{5,}\s*(\S+)\s+vs\s+(\S+)[^#]*#{5,}")
# ★ HP는 음수가 될 수 있다(격추 시 tgtHP=-0.0025). 부호를 빼면 격추된 판을 통째로 놓친다.
SEED = re.compile(
    r"^\[seed\s+(\d+)\]\s+reward=\s*(-?[\d.]+)\s+ownHP=(-?[\d.]+)\s+tgtHP=(-?[\d.]+)\s*(.*)$"
)


def parse(paths):
    """{(버전, 상대): [ (seed, reward, ownHP, tgtHP, 종료사유), ... ]}"""
    out = OrderedDict()
    for p in paths:
        cur = None
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = HDR.match(line.strip())
                if m:
                    cur = (m.group(1), m.group(2))
                    # 같은 상대가 여러 로그에 있으면 마지막 것으로 덮는다(재측정분 우선)
                    out[cur] = []
                    continue
                if cur is None:
                    continue
                m = SEED.match(line.strip())
                if m:
                    out[cur].append(
                        (int(m.group(1)), float(m.group(2)),
                         float(m.group(3)), float(m.group(4)), m.group(5).strip())
                    )
    return out


def summarize(rows):
    """시드 목록 -> (승, 무, 패, 준, 받은, 순이득, 최대기여시드비중%).

    판정은 규정 제6조(HP 비교). HP는 격추 시 음수가 될 수 있다.
    """
    w = sum(1 for r in rows if r[2] > r[3])
    l = sum(1 for r in rows if r[2] < r[3])
    d = len(rows) - w - l
    dealt = sum(1.0 - r[3] for r in rows)
    taken = sum(1.0 - r[2] for r in rows)
    net = dealt - taken
    per = [(1.0 - r[3]) - (1.0 - r[2]) for r in rows]
    top = (max(per) / net * 100.0) if (per and net > 0) else 0.0
    return w, d, l, dealt, taken, net, top


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    # 콘솔이 cp949여도 깨지지 않게
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    data = parse(sys.argv[1:])

    print(f"{'상대':<22}{'승':>4}{'무':>4}{'패':>4}{'  준':>9}{'  받은':>9}{'  순이득':>10}{'  최대시드':>10}")
    print("-" * 76)
    tw = td = tl = 0
    tg = tt = 0.0
    for (ver, opp), rows in data.items():
        if not rows:
            print(f"{opp:<22}{'— 측정 실패(SUMMARY 없음)':>40}")
            continue
        w, d, l, dealt, taken, net, top = summarize(rows)
        tw += w; td += d; tl += l; tg += dealt; tt += taken
        print(f"{opp:<22}{w:>4}{d:>4}{l:>4}{dealt:>9.4f}{taken:>9.4f}{net:>10.4f}{top:>9.1f}%")
    print("-" * 76)
    print(f"{'합계':<22}{tw:>4}{td:>4}{tl:>4}{tg:>9.4f}{tt:>9.4f}{tg - tt:>10.4f}")
    print(f"\n{len(data)}상대 / {sum(len(v) for v in data.values())}판")


if __name__ == "__main__":
    main()
