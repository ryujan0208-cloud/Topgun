# -*- coding: utf-8 -*-
"""대회 공식 WEZ 규칙 — 진단 도구 공용 모듈.

★ 2026-08-06 신설. 이유:
  진단 도구들이 각자 `ATA <= 1.0도`, `152.4~914.4m` 를 **하드코딩**하고 있었는데,
  대회 실제 규칙은 **교전 경과 시간에 따라 3단계로 완화**된다(오리엔테이션 PPT 슬라이드 7).
  즉 우리 도구는 200초 내내 Phase 1 기준으로만 재고 있었다 = 후반 득점을 통째로 못 봤다.

  오늘만 도구 상수 문제가 네 번 나왔다(turn_perf / alt_trace / ata_split / bfm_syllabus).
  같은 값을 여러 파일에 흩어 두면 반드시 어긋나므로 **한 곳에 모은다.**

규칙:
    Phase 1 (t >=   0s) : LOS < 1도, 500~3000ft, 계수 1.0
    Phase 2 (t >= 100s) : LOS < 2도, 500~3500ft, 계수 0.3
    Phase 3 (t >= 150s) : LOS < 3도, 500~4000ft, 계수 0.1
  "하위 Phase에 적이 위치하는 경우 하위 phase의 대미지 적용"
    -> 활성 phase 중 **최대 대미지**를 채택(좁은 콘에 있으면 높은 계수 유지).

  콘 부피비 1 : 6.36 : 21.37 이므로 기대 대미지 1.0 : 1.9 : 2.1
    = **후반 phase가 오히려 유리**하다(정밀도보다 물량).

주의: 거리 감쇠 공식은 대회가 공개하지 않았다("거리 비례"만 명시).
      로컬 공식 (max-d)/(max-min) 을 phase별 사거리로 일반화한 것이다.
"""
from __future__ import annotations

FEET = 0.30480

PHASES = [
    dict(name="P1", start_s=0.0,   los_deg=1.0, coeff=1.0,
         min_m=500 * FEET, max_m=3000 * FEET),
    dict(name="P2", start_s=100.0, los_deg=2.0, coeff=0.3,
         min_m=500 * FEET, max_m=3500 * FEET),
    dict(name="P3", start_s=150.0, los_deg=3.0, coeff=0.1,
         min_m=500 * FEET, max_m=4000 * FEET),
]

# 어떤 phase에서도 쓰이지 않는 절대 한계(도구의 '사거리 체류' 집계용)
ABS_MIN_M = min(p["min_m"] for p in PHASES)
ABS_MAX_M = max(p["max_m"] for p in PHASES)


def active(t):
    """시각 t에 활성화된 phase 목록."""
    return [p for p in PHASES if t >= p["start_s"]]


def hit(t, dist_m, ata_deg):
    """사격 성립 여부 + 어느 phase로 성립했는지. 성립 안 하면 (False, None)."""
    best = None
    for p in active(t):
        if p["min_m"] <= dist_m <= p["max_m"] and abs(ata_deg) <= p["los_deg"]:
            if best is None or p["coeff"] > best["coeff"]:
                best = p
    return (best is not None), (best["name"] if best else None)


def damage(t, dist_m, ata_deg, dt=1.0):
    """해당 틱의 대미지(계수 적용). 성립 안 하면 0."""
    best = 0.0
    for p in active(t):
        if not (p["min_m"] <= dist_m <= p["max_m"]):
            continue
        if abs(ata_deg) > p["los_deg"]:
            continue
        base = p["max_m"] - p["min_m"]
        if base <= 0:
            continue
        d = p["coeff"] * ((p["max_m"] - dist_m) / base) * dt
        if d > best:
            best = d
    return best


def describe():
    out = ["대회 WEZ 규칙 (PPT 슬라이드 7)"]
    for p in PHASES:
        out.append(f"  {p['name']}: t>={p['start_s']:5.0f}s  LOS<{p['los_deg']:.0f}deg  "
                   f"{p['min_m']:.1f}~{p['max_m']:.1f}m  계수 {p['coeff']}")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
    print(describe())
    print("\n예시 — 거리 600m, ATA 2.5도:")
    for t in (50, 120, 170):
        ok, ph = hit(t, 600.0, 2.5)
        print(f"  t={t:3d}s -> {'성립' if ok else '불성립':4} ({ph or '-'})  "
              f"대미지 {damage(t, 600.0, 2.5):.4f}")
