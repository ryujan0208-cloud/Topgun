# -*- coding: utf-8 -*-
"""절제 실험 판정 — 사전등록(experiments/ablation/PREREG_2026-08-08.md) 기준을 그대로 적용한다.

기준을 코드에 박아두는 이유: 결과를 보고 나서 손으로 계산하면 무의식적으로 기준이 움직인다.

  KEEP(짐을 진다)   : Δ승 <= -4  또는  Δ순이득 <= -3.0
  REMOVE 후보       : Δ승 >= -1  그리고 Δ순이득 >= -1.0
  보류              : 그 외

집계값만 보지 않도록 **최대 기여 시드 비중**을 항상 함께 출력한다.

사용: python tools_diag/ablation_report.py
"""
import re
import sys
from collections import OrderedDict, defaultdict

HDR = re.compile(r"^#{5,}\s*(\S+)\s+vs\s+(\S+)[^#]*#{5,}")
SEED = re.compile(
    r"^\[seed\s+(\d+)\]\s+reward=\s*(-?[\d.]+)\s+ownHP=(-?[\d.]+)\s+tgtHP=(-?[\d.]+)"
)

# 선별 세트. onecircle/sync는 최대기여시드 112.5%/50.2%로 이 표본 크기에선 분산이라 제외.
OPPS = ["ACE", "AIP_kwon.dll", "AIP_v7.dll", "SEARCH", "STRAIGHT",
        "AIP_jink.dll", "AIP_junghwan.dll"]

BASE_LOGS = ["_rerule.log", "_baseline.log"]
ABL_LOGS = ["_ablate_A.log", "_ablate_B.log"]
TAGS = ["v31", "v21", "v17", "v27", "v32clamp", "v18dive", "v23corner"]


def parse(paths):
    """{(라벨, 상대): [(ownHP, tgtHP), ...]}"""
    out = OrderedDict()
    for p in paths:
        cur = None
        try:
            f = open(p, "r", encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        with f:
            for line in f:
                s = line.strip()
                m = HDR.match(s)
                if m:
                    cur = (m.group(1), m.group(2))
                    out[cur] = []
                    continue
                if cur is None:
                    continue
                m = SEED.match(s)
                if m:
                    out[cur].append((float(m.group(3)), float(m.group(4))))
    return out


def stats(rows):
    w = sum(1 for o, t in rows if o > t)
    l = sum(1 for o, t in rows if o < t)
    d = len(rows) - w - l
    per = [(1.0 - t) - (1.0 - o) for o, t in rows]      # 시드별 순이득
    net = sum(per)
    top = (max(per) / net * 100.0) if net > 0 else 0.0
    return w, d, l, net, top, per


def verdict(dw, dnet):
    if dw <= -4 or dnet <= -3.0:
        return "KEEP  (짐을 진다)"
    if dw >= -1 and dnet >= -1.0:
        return "REMOVE 후보"
    return "보류"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    base = parse(BASE_LOGS)
    abl = parse(ABL_LOGS)

    # v32 기준선 (선별 7상대)
    b = {}
    for (lab, opp), rows in base.items():
        if opp in OPPS and rows:
            b[opp] = rows
    missing = [o for o in OPPS if o not in b]
    if missing:
        print(f"※ 기준선 없음: {missing}")

    bw = bd = bl = 0
    bnet = 0.0
    for o in OPPS:
        if o in b:
            w, d, l, net, _, _ = stats(b[o])
            bw += w; bd += d; bl += l; bnet += net
    print(f"v32 기준선 (7상대 {sum(len(b[o]) for o in b)}판): "
          f"{bw}승 {bd}무 {bl}패 / 순이득 {bnet:+.4f}")
    print()

    # 절제별
    print(f"{'절제':<12}{'승':>4}{'무':>4}{'패':>4}{'Δ승':>6}{'순이득':>10}{'Δ순이득':>10}   판정")
    print("-" * 78)
    results = {}
    for tag in TAGS:
        aw = ad = al = 0
        anet = 0.0
        per_opp = {}
        n = 0
        for o in OPPS:
            key = (f"ablate={tag}", o)
            rows = abl.get(key)
            if not rows:
                continue
            w, d, l, net, top, per = stats(rows)
            aw += w; ad += d; al += l; anet += net; n += len(rows)
            per_opp[o] = (w, d, l, net, top)
        if n == 0:
            print(f"{tag:<12}  — 데이터 없음")
            continue
        dw = aw - bw
        dnet = anet - bnet
        results[tag] = (aw, ad, al, anet, dw, dnet, per_opp)
        print(f"{tag:<12}{aw:>4}{ad:>4}{al:>4}{dw:>+6}{anet:>10.4f}{dnet:>+10.4f}   {verdict(dw, dnet)}")

    # 상대별 분해
    print()
    print("=" * 78)
    print("상대별 순이득 (v32 -> 절제)   ※ 총량이 같아도 유형별로 갈리면 그게 더 중요하다")
    print("=" * 78)
    hdr = f"{'상대':<20}{'v32':>9}"
    for tag in TAGS:
        hdr += f"{tag:>10}"
    print(hdr)
    print("-" * 78)
    for o in OPPS:
        if o not in b:
            continue
        _, _, _, bn, _, _ = stats(b[o])
        row = f"{o:<20}{bn:>9.3f}"
        for tag in TAGS:
            pe = results.get(tag, (0,)*7)[6] if tag in results else {}
            row += f"{pe[o][3]:>10.3f}" if o in pe else f"{'-':>10}"
        print(row)

    # 승수 분해
    print()
    print(f"{'상대':<20}{'v32':>9}", end="")
    for tag in TAGS:
        print(f"{tag:>10}", end="")
    print("   (승수)")
    print("-" * 78)
    for o in OPPS:
        if o not in b:
            continue
        w, _, _, _, _, _ = stats(b[o])
        row = f"{o:<20}{w:>9}"
        for tag in TAGS:
            pe = results.get(tag, (0,)*7)[6] if tag in results else {}
            row += f"{pe[o][0]:>10}" if o in pe else f"{'-':>10}"
        print(row)

    # 최대 기여 시드 비중
    print()
    print("=" * 78)
    print("최대 기여 시드 비중 — 50% 넘으면 그 결과는 효과가 아니라 분산이다")
    print("=" * 78)
    print(f"{'상대':<20}{'v32':>9}", end="")
    for tag in TAGS:
        print(f"{tag:>10}", end="")
    print()
    print("-" * 78)
    for o in OPPS:
        if o not in b:
            continue
        _, _, _, _, bt, _ = stats(b[o])
        row = f"{o:<20}{bt:>8.0f}%"
        for tag in TAGS:
            pe = results.get(tag, (0,)*7)[6] if tag in results else {}
            row += f"{pe[o][4]:>9.0f}%" if o in pe else f"{'-':>10}"
        print(row)


if __name__ == "__main__":
    main()
