# -*- coding: utf-8 -*-
"""조종 권한이 어디서 죽는지 잰다 — Controller_CY의 세 계수를 로그에서 재현한다.

[왜] 사거리 안 우리 ATA 중앙이 7.65도인데, 그 각도면
      ERROR_Effect = clamp(7.65/6 + adj, 0, 1.5) = 1.5  -> 이미 포화
    이므로 "가까워서 권한이 준다"는 설명은 성립하지 않는다(내 초안을 스스로 기각).
    남은 계수는 Roll_Effect 와 Horizon_Effect 다.

      Roll_Effect    = 1 - clamp(|UTAngle_deg| / 90, 0, 1)
      Horizon_Effect = 1 if |UTAngle_deg| <= 90 else 0.5
      PitchCMD       = clamp(ERROR_Effect * Roll_Effect * Horizon_Effect * -1, -1, 1)

    UTAngle = Up 벡터와 '표적 방향의 기수축 수직성분' 사이 각.
    표적이 양력벡터 평면 밖이면 Roll_Effect -> 0 이 되어 피치가 죽는다.

[자기 검산] Forward·Up ~ 0, |Up| ~ 1 을 확인하고 시작한다. 안 맞으면 자세 재현이 틀린 것이다.

[한계] VP를 모르므로 '상대 현재 위치'를 VP로 근사한다.
  lead_bias.py 실측에서 우리 기수가 99.2% 틱에서 현재 위치에 더 가까웠으므로 타당한 근사이나,
  근사임을 잊지 말 것. Roll_Effect의 절대값보다 **두 매치업의 차이**를 본다.

사용: python tools_diag/authority.py <own.csv> <tgt.csv>
"""
from __future__ import annotations
import argparse, csv, math, sys, statistics as st

try:
    import pymap3d as pm
except ImportError:
    sys.exit("pymap3d 필요 (conda env 'aip')")


def load(p):
    out = []
    for r in csv.DictReader(open(p, newline="", encoding="utf-8-sig", errors="replace")):
        try:
            out.append(dict(t=float(r["Time"]), lat=float(r["Latitude"]), lon=float(r["Longitude"]),
                            alt=float(r["Altitude"]), roll=float(r["Roll (deg)"]),
                            pitch=float(r["Pitch (deg)"]), yaw=float(r["Yaw (deg)"])))
        except (ValueError, KeyError):
            continue
    return out


def axes(roll_d, pitch_d, yaw_d):
    """ENU(동,북,상)에서 기수/상/우 단위벡터. yaw는 compass(북 기준 시계방향) — 실측 확인된 규약."""
    r, p, y = map(math.radians, (roll_d, pitch_d, yaw_d))
    cp = math.cos(p)
    F = (cp * math.sin(y), cp * math.cos(y), math.sin(p))
    # roll=0 일 때의 Up: 기수를 피치만큼 든 상태에서 위쪽
    U0 = (-math.sin(p) * math.sin(y), -math.sin(p) * math.cos(y), math.cos(p))
    R0 = (math.cos(y), -math.sin(y), 0.0)          # 오른쪽(수평)
    cr, sr = math.cos(r), math.sin(r)
    U = tuple(U0[i] * cr + R0[i] * (-sr) for i in range(3))   # roll 회전
    R = tuple(R0[i] * cr + U0[i] * sr for i in range(3))
    return F, U, R


def dot(a, b): return sum(x * y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def norm(a): return math.sqrt(dot(a, a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("own"); ap.add_argument("tgt")
    ap.add_argument("--min", dest="rmin", type=float, default=500 * 0.3048)
    ap.add_argument("--max", dest="rmax", type=float, default=3000 * 0.3048)
    a = ap.parse_args()

    U_, T_ = load(a.own), load(a.tgt)
    n = min(len(U_), len(T_))
    if n < 3:
        sys.exit("행 부족")
    lat0, lon0, alt0 = U_[0]["lat"], U_[0]["lon"], U_[0]["alt"]
    enu = lambda r: pm.geodetic2enu(r["lat"], r["lon"], r["alt"], lat0, lon0, alt0)

    # 자기 검산
    F, Up, Rt = axes(37.0, 12.0, 200.0)
    ortho = abs(dot(F, Up))
    if ortho > 1e-6 or abs(norm(Up) - 1) > 1e-6:
        sys.exit(f"★ 자세 재현 실패: F·Up={ortho:.2e}, |Up|={norm(Up):.6f}")

    los_l, roll_l, pitch_l, err_l = [], [], [], []
    for i in range(n):
        po, pt = enu(U_[i]), enu(T_[i])
        d = sub(pt, po); dm = norm(d)
        if not (a.rmin <= dm <= a.rmax):
            continue
        F, Up, Rt = axes(U_[i]["roll"], U_[i]["pitch"], U_[i]["yaw"])
        los = math.degrees(math.acos(max(-1, min(1, dot(F, d) / dm))))
        proj = sub(d, tuple(dot(d, F) * F[k] for k in range(3)))     # 기수축 수직성분
        pn = norm(proj)
        if pn < 1e-9:
            continue
        ut = math.degrees(math.acos(max(-1, min(1, dot(Up, tuple(proj[k] / pn for k in range(3)))))))
        err = min(1.5, los / 6.0)                                     # 적분항 제외(상한 0.25)
        rolle = 1 - min(1.0, abs(ut) / 90.0)
        hor = 1.0 if abs(ut) <= 90 else 0.5
        los_l.append(los); roll_l.append(rolle); err_l.append(err)
        pitch_l.append(min(1.0, err * rolle * hor))

    if not los_l:
        print("사거리 체류 0틱"); return
    q = lambda v, p: sorted(v)[int(len(v) * p)]
    print(f"사거리 안 {len(los_l)}틱")
    print(f"  LOS            중앙 {st.median(los_l):6.2f}도")
    print(f"  ERROR_Effect   중앙 {st.median(err_l):6.3f}   (1.0 이상이면 포화)")
    print(f"  Roll_Effect    중앙 {st.median(roll_l):6.3f}   5% {q(roll_l,0.05):.3f}  95% {q(roll_l,0.95):.3f}")
    print(f"  실효 PitchCMD  중앙 {st.median(pitch_l):6.3f}   (1.0이면 최대)")
    sat = sum(1 for x in pitch_l if x >= 0.99)
    dead = sum(1 for x in pitch_l if x < 0.3)
    print(f"  피치 포화 {100*sat/len(pitch_l):5.1f}%   피치 억제(<0.3) {100*dead/len(pitch_l):5.1f}%")


if __name__ == "__main__":
    main()
