#pragma once
// ============================================================================
//  절제 실험 게이트 (연구용)
// ============================================================================
// [왜 필요한가 — 2026-08-08]
// v33~v39가 7연속 기각됐다. 전부 "이해하지 못하는 토대(v32) 위에 얹은 추가"였다.
// v32가 무엇으로 만들어졌는지 우리는 모른다:
//   - 기각한 v31 하강나선 코드가 소스에 남아 v32에 들어가 있다
//   - 최대 지분 기능인 v21 뱅크예측(발동률 95~97%)은 한 번도 검증된 적이 없다
//   - v27 종말조준은 발동률 0.3~5.7%뿐인데 v27의 간판 개선이었다
// => 8번째를 더하기 전에, 있는 것을 하나씩 빼서 무엇이 짐을 지고 있는지 잰다.
//
// [설계 — 빌드를 여러 번 하지 않는다]
// 절제마다 다시 빌드하면 빌드 간 차이가 결과에 섞인다(무엇을 재는지 알 수 없게 된다).
// DLL은 하나만 만들고 환경변수로 절제 대상을 고른다.
//
//   TOPGUN_ABLATE 미설정  ->  전부 활성 = v32 그대로 (반드시 v32와 동일해야 한다)
//   TOPGUN_ABLATE=v21     ->  v21 뱅크 횡예측만 끈다
//
// [★ 반드시 먼저 할 것] 미설정 상태로 돌린 결과가 AIP_v32.dll과 **동일**한지 확인한다.
//   동일하지 않으면 게이트를 넣는 과정에서 뭔가 바꾼 것이고, 그 뒤 측정은 전부 무의미하다.
//   (코덱스가 CV01에서 계측 DLL의 정상 경로 해시 일치로 검증한 방식과 같다)
//
// [제출 시] 환경변수가 없으면 완전한 무동작이므로 그대로 두어도 안전하다.
//   다만 제출 전 `TOPGUN_ABLATE`가 설정돼 있지 않은지 확인할 것.

#include <cstdlib>
#include <cstring>

namespace Ablation
{
    // 환경변수를 매 틱 읽지 않는다(10Hz x 200초 x 배치). 최초 1회만.
    inline const char* selected()
    {
        static bool  init = false;
        static const char* sel = nullptr;
        if (!init) {
            init = true;
#if defined(_MSC_VER)
            // MSVC는 getenv에 경고를 낸다. _dupenv_s는 해제가 필요해 정적 버퍼로 받는다.
            static char buf[64];
            size_t n = 0;
            if (getenv_s(&n, buf, sizeof(buf), "TOPGUN_ABLATE") == 0 && n > 1) sel = buf;
#else
            sel = std::getenv("TOPGUN_ABLATE");
#endif
        }
        return sel;
    }

    // tag 기능이 "꺼져 있는가". 환경변수 미설정이면 항상 false = 전부 활성 = v32.
    inline bool off(const char* tag)
    {
        const char* sel = selected();
        if (sel == nullptr || sel[0] == '\0') return false;
        return std::strcmp(sel, tag) == 0;
    }
}
