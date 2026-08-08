# -*- coding: utf-8 -*-
"""배치 로그에서 실행별 **최종 DUTY 발동률**을 뽑는다.

[왜] 점수만 보고 판정하면 "왜 그렇게 됐는지"를 모른다. 특히 dt 수정은
발동률이 급감해야 수정이 먹은 것이다 — 안 변하면 코드가 안 탄 것이다.
DUTY는 누적 카운터라 각 실행의 **마지막 줄**이 그 실행의 총계다.

⚠ DLL은 콘솔 코드페이지로 찍으므로 한글이 깨질 수 있다. 숫자만 위치로 읽는다.

사용: python tools_diag/duty_report.py <로그> [<로그> ...]
"""
import re
import sys

HDR = re.compile(r"^#{5,}\s*(\S+)\s+vs\s+(\S+)[^#]*#{5,}")
# [DUTY] team=1 ticks=16800 <이름>=5.48% <이름>=0% ... — 이름이 깨져도 순서는 고정이다
NUM = re.compile(r"=([\d.]+)%")
TICKS = re.compile(r"ticks=(\d+)")
COLS = ["v27종말", "v21뱅크", "v17궤도", "v17슬롯", "상승클램프", "강하클램프",
        "v23코너조건", "v23코너적용"]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        return

    runs = []            # (라벨, 상대, ticks, [비율...])
    cur = None
    last = None
    for path in sys.argv[1:]:
        try:
            f = open(path, "r", encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        with f:
            for line in f:
                s = line.strip()
                m = HDR.match(s)
                if m:
                    if cur and last:
                        runs.append((cur[0], cur[1], last[0], last[1]))
                    cur, last = (m.group(1), m.group(2)), None
                    continue
                if cur is None or "[DUTY]" not in s or "team=1" not in s:
                    continue
                t = TICKS.search(s)
                v = NUM.findall(s)
                if t and len(v) >= len(COLS):
                    last = (int(t.group(1)), [float(x) for x in v[:len(COLS)]])
    if cur and last:
        runs.append((cur[0], cur[1], last[0], last[1]))

    if not runs:
        print("DUTY 라인이 없다. 배치에서 [DUTY]를 필터로 버렸는지 확인할 것.")
        return

    hdr = f"{'변형':<13}{'상대':<20}{'틱':>7}"
    for c in COLS:
        hdr += f"{c:>12}"
    print(hdr)
    print("-" * len(hdr))
    for lab, opp, ticks, vals in runs:
        row = f"{lab:<13}{opp:<20}{ticks:>7}"
        for x in vals:
            row += f"{x:>11.1f}%"
        print(row)


if __name__ == "__main__":
    main()
