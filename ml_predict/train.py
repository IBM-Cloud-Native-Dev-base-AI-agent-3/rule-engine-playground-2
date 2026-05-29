import os
import pickle
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

# 5대 분류 모델 임포트
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC

def train_and_compare_models(data_path="../data/processed/hope_ml_dataset.csv"):
    print("Loading dataset...")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at: {data_path}. Please run prep_dataset.py first.")
        
    df = pd.read_csv(data_path)
    
    # 1. 분리 전처리: Feature(X)와 Target(y) 정의
    # 의사결정 나무 등이 쉽게 매칭하지 못하도록 인위적으로 계산된 순위(derived_priority) 및 가점(derived_score) 컬럼은 제거합니다.
    # 모델이 순수한 원시 신청인 팩트 데이터(소득 비율, 자산 금액 등)로부터 비선형 조건 경계를 학습하도록 만듭니다!
    X = df.drop(columns=["derived_priority", "derived_score", "Pass"])
    y = df["Pass"]
    
    # 2. Preprocessor 정의 (ColumnTransformer 활용)
    # 범주형 변수 (One-Hot Encoding)
    categorical_features = ["gender", "schoolLocation", "applied_danji"]
    # 수치형 변수 (Standard Scaling)
    numeric_features = ["incomePercent", "totalAsset", "carValue", "subscriptionCount"]
    # 이진 변수 & 순위 타겟값 (인코딩 없이 유지)
    passthrough_features = [
        "isHomeOwner", "isMarried", "isGraduateStudent", "isGraduatedOrSuspended", 
        "hasCar", "isPriority1Eligible", "isRecipient", "isSingleParentFamily", 
        "isParentsHomeless", "isApplicantDisabled", "isParentsDisabled", "applied_priority"
    ]
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), categorical_features),
            ("num", StandardScaler(), numeric_features),
            ("pass", "passthrough", passthrough_features)
        ]
    )
    
    # 3. Train / Test 분할 (계층적 분할 적용하여 라벨 비율 균등 유지)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Dataset Split Completed:")
    print(f"  Train samples: {X_train.shape[0]}")
    print(f"  Test samples: {X_test.shape[0]}")
    
    # 4. 5대 분류 모델 정의
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(max_depth=15, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "Support Vector Machine": SVC(probability=True, random_state=42)
    }
    
    results = []
    trained_pipelines = {}
    
    print("\nTraining models and evaluating performance...")
    
    for name, model in models.items():
        # 전처리 파이프라인과 모델 결합 (Best Practice)
        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("classifier", model)
        ])
        
        # 모델 학습
        pipeline.fit(X_train, y_train)
        trained_pipelines[name] = pipeline
        
        # 예측값 및 확률값 도출
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else [0] * len(y_test)
        
        # 성능 지표 평가
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_prob) if len(np.unique(y_prob)) > 1 else 0.5
        
        results.append({
            "Model": name,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1-Score": f1,
            "ROC-AUC": auc
        })
        
        print(f"  [Trained] {name:<24} - Accuracy: {acc*100:.2f}% | F1-Score: {f1:.4f}")
        
    # 5. 결과를 데이터프레임으로 변환하여 Markdown 표로 포맷팅
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by="F1-Score", ascending=False)
    
    print("\n==========================================================================")
    print("                     머신러닝 분류 모델 성능 비교 성적표")
    print("==========================================================================")
    markdown_table = results_df.to_markdown(index=False, floatfmt=".4f")
    print(markdown_table)
    print("==========================================================================\n")
    
    # 6. 최적의 모델 저장 (F1-Score 기준)
    best_model_name = results_df.iloc[0]["Model"]
    best_pipeline = trained_pipelines[best_model_name]
    best_f1 = results_df.iloc[0]["F1-Score"]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_save_path = os.path.join(script_dir, "best_model.pkl")
    
    with open(model_save_path, "wb") as f:
        pickle.dump(best_pipeline, f)
        
    print(f"[성공] 최적의 성능을 낸 모델은 '{best_model_name}' (F1-Score: {best_f1:.4f}) 입니다.")
    print(f"가장 신뢰성 높은 전처리 파이프라인 및 가중치가 통합 보관된 모델을 저장했습니다: {model_save_path}")
    
    return markdown_table

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(script_dir, "../data/processed/hope_ml_dataset.csv")
    train_and_compare_models(data_file)
