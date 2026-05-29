import os
import sys
import pickle
import pandas as pd

# Set stdout to UTF-8 to prevent encoding errors on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def predict_admission_odds():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, "best_model.pkl")
    
    print("Loading the best-performing machine learning model...")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Best model not found at: {model_path}. Please run train.py first.")
        
    with open(model_path, "rb") as f:
        pipeline = pickle.dump if False else pickle.load(f)
        
    print("[Success] Model loaded successfully.")
    
    # Define 3 highly distinct mock applicants for evaluation
    mock_applicants = [
        {
            "Name": "A (1순위 기초수급+한부모 만점 청년)",
            "gender": "여성",
            "isHomeOwner": 0,
            "isMarried": 0,
            "schoolLocation": "서울",
            "isGraduateStudent": 0,
            "isGraduatedOrSuspended": 0,
            "incomePercent": 30,             # 1순위 소득 면제 (낮은 값)
            "totalAsset": 20_000_000,        # 1순위 자산 면제 (낮은 값)
            "carValue": 0,
            "hasCar": 0,
            "isPriority1Eligible": 1,
            "isRecipient": 1,                # 수급자 (3점)
            "isSingleParentFamily": 1,       # 한부모 (3점)
            "isParentsHomeless": 1,          # 부모 무주택 (2점)
            "isApplicantDisabled": 0,
            "isParentsDisabled": 0,
            "subscriptionCount": 25,         # 청약 GTE 24 (3점) -> 가점 총 11점 만점!
            "applied_danji": "연남공공원룸텔",
            "applied_priority": 1            # 1순위 신청
        },
        {
            "Name": "B (2순위 부모 자산 초과 고자산가)",
            "gender": "여성",
            "isHomeOwner": 0,
            "isMarried": 0,
            "schoolLocation": "서울",
            "isGraduateStudent": 0,
            "isGraduatedOrSuspended": 0,
            "incomePercent": 90,
            "totalAsset": 350_000_000,       # 3억 5천만 원 (2순위 한도 3.37억 초과!)
            "carValue": 15_000_000,
            "hasCar": 1,
            "isPriority1Eligible": 0,
            "isRecipient": 0,
            "isSingleParentFamily": 0,
            "isParentsHomeless": 1,          # 부모 무주택 (2점)
            "isApplicantDisabled": 0,
            "isParentsDisabled": 0,
            "subscriptionCount": 12,         # 청약 (2점) -> 가점은 있지만 자산 컷 탈락 예상!
            "applied_danji": "연남공공원룸텔",
            "applied_priority": 2            # 2순위 신청
        },
        {
            "Name": "C (정릉 남성 3순위 합격권 대학생)",
            "gender": "남성",
            "isHomeOwner": 0,
            "isMarried": 0,
            "schoolLocation": "서울",
            "isGraduateStudent": 0,
            "isGraduatedOrSuspended": 0,
            "incomePercent": 60,             # 3순위 소득 한도 충족
            "totalAsset": 45_000_000,        # 3순위 자산 한도 충족
            "carValue": 0,
            "hasCar": 0,                     # 3순위 차량 무소유 충족
            "isPriority1Eligible": 0,
            "isRecipient": 0,
            "isSingleParentFamily": 0,
            "isParentsHomeless": 1,          # 부모 무주택 (2점)
            "isApplicantDisabled": 0,
            "isParentsDisabled": 0,
            "subscriptionCount": 8,          # 청약 (1점) -> 정릉 남성 3순위 커트라인은 0점이므로 합격 예상!
            "applied_danji": "희망하우징(정릉동 1036)",
            "applied_priority": 3            # 3순위 신청
        }
    ]
    
    # Convert mock applicants into pandas DataFrame
    df_mock = pd.DataFrame(mock_applicants)
    X_mock = df_mock.drop(columns=["Name"])
    
    # Run prediction and probability estimation
    predictions = pipeline.predict(X_mock)
    probabilities = pipeline.predict_proba(X_mock)[:, 1]
    
    print("\n==========================================================================")
    print("                     희망하우징 모의 지원자 서류심사 합격 예측 결과")
    print("==========================================================================")
    
    for idx, applicant in df_mock.iterrows():
        name = applicant["Name"]
        danji = applicant["applied_danji"]
        prio = applicant["applied_priority"]
        pred_label = "★합격예상 (PASS)★" if predictions[idx] == 1 else "❌탈락예상 (FAIL)❌"
        prob_pct = probabilities[idx] * 100
        
        print(f"▶ 지원자: {name}")
        print(f"  지원 정보: {danji} | {prio}순위 신청")
        print(f"  예측 결과: {pred_label} (합격 가능 확률: {prob_pct:.2f}%)")
        print("-" * 74)
        
    print("==========================================================================\n")

if __name__ == "__main__":
    predict_admission_odds()
