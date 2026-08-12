# -*- coding: utf-8 -*-
"""라운드2·3 배치(_r23_*.log)를 (라운드 x 기하) 셀로 집계한다.
헤더 형식: '########## <버전> / 라운드<n> / <기하> / jh2 ##########'
"""
import re, sys
def load(path):
    cur=None; acc={}
    for l in open(path, encoding='utf-8', errors='replace'):
        m=re.match(r'#+\s+(\S+)\s+/\s+(라운드\d)\s+/\s+(\S+)\s+/', l)
        if m: cur=(m.group(2), m.group(3)); acc.setdefault(cur, [])
        m2=re.match(r'SUMMARY dealt=([-\d.]+) taken=([-\d.]+)', l)
        if m2 and cur: acc[cur].append((float(m2.group(1)), float(m2.group(2))))
    return acc
def wdl(r):
    w=sum(1 for d,t in r if d>t); L=sum(1 for d,t in r if d<t)
    return w, len(r)-w-L, L, sum(d-t for d,t in r)
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    a=load(sys.argv[1]); b=load(sys.argv[2]) if len(sys.argv)>2 else None
    keys=sorted(a)
    print(f"{'라운드':<8}{'기하':<12}{'기준선(2번째 인자)':>20}{'대상(1번째)':>18}{'Δ승':>5}{'Δ패':>5}")
    print('-'*70)
    ta=[0,0,0,0.0]; tb=[0,0,0,0.0]
    for k in keys:
        wa=wdl(a[k]); ta=[ta[i]+wa[i] for i in range(4)]
        if b and k in b:
            wb=wdl(b[k]); tb=[tb[i]+wb[i] for i in range(4)]
            flag=' ←퇴행' if (wa[2]-wb[2])>=2 else ''
            print(f"{k[0]:<8}{k[1]:<12}{f'{wb[0]}/{wb[1]}/{wb[2]} {wb[3]:+.2f}':>20}"
                  f"{f'{wa[0]}/{wa[1]}/{wa[2]} {wa[3]:+.2f}':>18}{wa[0]-wb[0]:>+5}{wa[2]-wb[2]:>+5}{flag}")
        else:
            print(f"{k[0]:<8}{k[1]:<12}{'-':>20}{f'{wa[0]}/{wa[1]}/{wa[2]} {wa[3]:+.2f}':>18}")
    print('-'*70)
    if b:
        print(f"{'합계':<20}{f'{tb[0]}/{tb[1]}/{tb[2]} {tb[3]:+.2f}':>20}"
              f"{f'{ta[0]}/{ta[1]}/{ta[2]} {ta[3]:+.2f}':>18}{ta[0]-tb[0]:>+5}{ta[2]-tb[2]:>+5}")
    else:
        print(f"{'합계':<20}{'':>20}{f'{ta[0]}/{ta[1]}/{ta[2]} {ta[3]:+.2f}':>18}")
