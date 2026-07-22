# -*- coding: utf-8 -*-
# 여러 에피소드가 연결된 tacview CSV에서 Time 되감김 기준으로 마지막 에피소드만 분리 저장
import csv, sys, os
R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
stamp = sys.argv[1]

for side, tag in (("ownship", "(F-16)[Blue]"), ("target", "(F-16)[Red]")):
    p = os.path.join(R, f"{stamp}_{side}_{tag}.csv")
    with open(p, newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    head, body = rows[0], rows[1:]
    ti = head.index("Time"); ai = head.index("Altitude")
    lo = head.index("Longitude"); la = head.index("Latitude")
    # 에피소드 경계 = 위치/고도 순간이동(리스폰). 1틱에 고도 800m+ 또는 수평 3km+ 점프
    starts = [0]
    for i in range(1, len(body)):
        dz = abs(float(body[i][ai]) - float(body[i-1][ai]))
        dxy = (abs(float(body[i][lo]) - float(body[i-1][lo])) +
               abs(float(body[i][la]) - float(body[i-1][la]))) * 111320.0
        if dz > 800.0 or dxy > 3000.0:
            starts.append(i)
    # 모든 에피소드를 개별 파일로 저장 (시드 k = k번째 에피소드)
    ends = starts[1:] + [len(body)]
    for k, (s, e) in enumerate(zip(starts, ends)):
        out = os.path.join(R, f"{stamp}_s{k:02d}_{side}_{tag}.csv")
        with open(out, "w", newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(head); w.writerows(body[s:e])
    print(f"{side}: {len(starts)}개 에피소드 분리 -> {stamp}_s00~s{len(starts)-1:02d}")
