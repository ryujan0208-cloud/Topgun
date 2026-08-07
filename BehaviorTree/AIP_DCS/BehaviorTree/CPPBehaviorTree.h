// Fill out your copyright notice in the Description page of Project Settings.

#pragma once
#include <iostream>
#include "./behaviortree_cpp_v3/bt_factory.h"
#include "./BT_Content/Task/TaskNodes.h"
#include "./BT_Content/Service/ServiceNodes.h"
#include "./BT_Content/Decorator/DecoratorNodes.h"
#include "../Geometry/Vector3.h"
#include "../Geometry/EulerAngle.h"
#include "../Geometry/Quaternion.h"
#include "./BT_Content/BlackBoard/CPPBlackBoard.h"
#include "./BT_Content/Functions.h"
#include "../Geometry/Controller_CY.h"


#define OriLAT 37.91455691666666
#define OriLOn 128.18188127777776

/*
	Unreal Engien 4 ??鍮꾪뿤鍮꾩뼱?몃━濡?留뚮뱺 RAIP瑜?C++ 湲곕컲??怨듭쭨 鍮꾪뿤鍮꾩뼱?몃━濡?援ы쁽?섍린 ?꾪븳 ?대옒??

	init()				: ?몃━ xml怨?媛??몃뱶?ㅼ쓣 load?섍퀬 釉붾옓蹂대뱶瑜?珥덇린???섎뒗 遺遺?
	RunCPPBT()			: 鍮꾪뿤鍮꾩뼱?몃━瑜??듯븯??異붿쟻???앹꽦
	Step()				: ?앹꽦??異붿쟻?먯쓣 已볦븘媛???ㅽ떛媛??앹꽦
	PreventLandCrash()	: 吏??異⑸룎 諛⑹? 湲곕뒫 ?⑥닔
	getBT_Text()		: 鍮꾪뿤鍮꾩뼱?몃━ ?대꼫?뚯씠??湲곕뒫?쇰줈 釉붾옓蹂대뱶????λ맂 鍮꾪뿤鍮꾩뼱?몃━??寃곗젙 怨쇱젙 String??遺덈윭?ㅻ뒗 遺遺?
	SetACM()			: ?좊Т??蹂듯빀?먯꽌 ?멸컙 議곗쥌?ш? ?꾧뎔湲곗쓽 ACM(EF/SF)瑜??섎룞?쇰줈 寃곗젙?섍린 ?꾪븳 ?⑥닔
	SetTarget()			: ?좊Т??蹂듯빀?먯꽌 ?멸컙 議곗쥌?ш? ?꾧뎔湲곗쓽 Target???섎룞??寃곗젙?섍린 ?꾪븳 ?⑥닔
*/
class  UCPPBehaviorTree
{

private:
	double f2m;
	double EQ_R;
	double P_R;
	double fr;
	double Req;
	double d2r;
	double m2f;
	double elev0;
	double aile0;
	double eccen;
	bool bInitialized;

private:
	//Lat, Lon, 怨좊룄??meter
	Vector3 LLAtoCartesian(Vector3 LLA, Vector3 BaseLLA);

public:	
	int ID;			//由щ늼?ㅽ솚寃쎌뿉???ъ슜?섎뒗 蹂??
	int ForceID;		//由ъ닕?ㅽ솚寃쎌뿉???ъ슜?섎뒗 蹂??
	// Sets default values for this component's properties
	UCPPBehaviorTree();
	~UCPPBehaviorTree();
	
	BT::BehaviorTreeFactory Factory;	//C++ 鍮꾪뿤鍮꾩뼱?몃━ 媛앹껜 ?대옒??
	BT::Tree tree;	// C++ 鍮꾪뿤鍮꾩뼱?몃━ ?몃━
	CPPBlackBoard* BB;	// C++ 鍮꾪뿤鍮꾩뼱 ?몃━??湲곕낯 釉붾옓蹂대뱶 諛⑹떇???곕젅湲??섏??대씪 ?곕줈 釉붾옓蹂대뱶 ?대옒?ㅻ? 援ы쁽?섏뿬 ?ъ슜
	StickController Controller; // ?쒖뼱湲? 鍮꾪뿤鍮꾩뼱?몃━?먯꽌 VP(異붿쟻?????앹꽦?섎㈃ 洹?VP瑜??ν븯???吏곸씠寃??섎뒗 Roll Pitch Yaw 而ㅻ찘??媛믪쓣 ?앹꽦
public:	
	
	
	//?몃━ xml怨?媛??몃뱶?ㅼ쓣 load?섍퀬 釉붾옓蹂대뱶瑜?珥덇린???섎뒗 遺遺?
	void init();	
	bool IsInitialized() const;

	/*
	鍮꾪뿤鍮꾩뼱?몃━瑜??듯븯??異붿쟻???앹꽦
		VP			: Cartesian 醫뚰몴怨? meter
		Throttle	: 0~1 ?ъ씠???곕줈?媛?
		AimmingMode : ?쒖뼱湲곗쓽 議곗쥌 紐⑤뱶瑜?寃곗젙
	*/
	void RunCPPBT(Vector3& VP, float& Throttle, bool& AimmingMode); //?쒕퉬???몃뱶 ??븷, ?붿떆???몃━

	/*
	鍮꾪뿤鍮꾩뼱?몃━?먯꽌 ?앹꽦??VP瑜??ν븯??鍮꾪뻾湲곌? 諛붾씪蹂대룄濡?鍮꾪뻾湲곌? ?吏곸씠寃??섎뒗 ?ㅽ떛媛믪쓣 ?앹꽦?섎뒗 ?⑥닔
		MyInfo					: ??鍮꾪뻾湲??뺣낫 (?꾩튂 ?먯꽭 ?띾룄 ? ?뺣낫??
		NumofOtherPlane			: ?꾩옣?먯꽌 ??鍮꾪뻾湲곌? ?꾨땶 ?ㅻⅨ 鍮꾪뻾湲곕뱾??媛쒖닔
		OthersInfo				: ??鍮꾪뻾湲곌? ?꾨땶 ?ㅻⅨ 鍮꾪뻾湲곕뱾???뺣낫 由ъ뒪??Array)
		VP						: ?붾쾭洹몄슜 Ref 蹂??
		Throttle				: ?붾쾭洹몄슜 Ref 蹂??
	*/
	StickValue Step(
		PlaneInfo MyInfo,
		int NumofOtherPlane,
		PlaneInfo* OthersInfo,
		Vector3& VP,
		float& Throttle,
		const Vector3* VPOverride = nullptr);

	Vector3 GetVP();

	//鍮꾪뿤鍮꾩뼱?몃━ ?명?????ㅼ젙 ?⑥닔
	void SetDeltaTime(double DT);
};
