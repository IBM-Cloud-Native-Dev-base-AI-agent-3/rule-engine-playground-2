# rule-engine-playground-2

https://github.com/IBM-Cloud-Native-Dev-base-AI-agent-3/rule-engine-playground 랑 다른 점. 
얘는 그냥 말그대로 룰엔진을 쓰는 법에 대해서 설명했다고 치자고. 

그럼 지금 2는 뭐냐? 
멘토링받고 세부적으로 실제 코드에 맞게 변경을 한거야. 

어떻게? 

간략하게 표현하면 이거지. 각 상품별로 자격요건(RULE)이 다르잖아. 
니까 각 상품별로 RULE을 다르게 해서 DB화 하자. 이거지. 
그래서 지금 있는 폴더는 뭐냐면, SH기준으로 모든 공고의 신청자격+입주선정기준+소득요건+가점 같은것만 긁어서 갖고왔어. 
그리고 이걸 LLM 한테 시켜가지고 RULE을 각각 만들거야. 알겠어? 
1편의 진화버전?이라고 볼수있지. 



---

## 🚀 새로운 컴퓨터에서 복제(Clone) 후 최초 실행 가이드 (Step-by-Step)

새로운 PC 환경에서 이 프로젝트 저장소를 내려받아 **룰 엔진용 MySQL 데이터베이스를 복구하고 전체 파이프라인(머신러닝 및 노트북)을 실행하는 방법**을 자세하게 안내해 드립니다.

### Step 1. 프로젝트 복제 (Clone) 및 진입
터미널을 열고 새 환경에 저장소를 클론한 뒤 해당 디렉토리로 들어갑니다.
```bash
git clone <저장소_URL>
cd rule-engine-playground-2
```

### Step 2. 로컬 MySQL 데이터베이스 생성
새 PC의 MySQL 서버에 접속하여 룰 엔진용 빈 데이터베이스를 하나 개설해 줍니다.
```sql
CREATE DATABASE rule_engine;
```

### Step 3. 접속 환경 변수 파일 (`.env`) 설정
프로젝트 루트 위치(`rule-engine-playground-2/.env`)에 환경 정보 파일을 신규 생성하고, 새 컴퓨터의 MySQL 접속 정보를 기입합니다.
* **파일 경로:** `rule-engine-playground-2/.env`
* **기입할 텍스트:**
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=여기에_새컴퓨터_MySQL_비밀번호_입력
DB_NAME=rule_engine
```
> ⚠️ **보안 경고:** 이 비밀번호가 깃허브 원격지에 노출되는 것을 막기 위해, 푸시(Push)하기 전 `.gitignore` 파일에 `.env`를 등록하시거나 `git rm --cached .env` 처리를 진행해 주세요.

### Step 4. 원클릭 테이블 구축 및 188개 규칙 복원 (Seeding)
터미널에서 아래 복원 명령어를 실행합니다.
```bash
python rules_pipeline/db_helper.py
```
* **작동 원리:** 빈 데이터베이스에 자동으로 설계 테이블 DDL(`schema.sql`)을 적용해 **5대 뼈대 테이블을 신규 구축**한 뒤, 백업 파일(`insert_rules.sql`)을 읽어와 **188개의 희망하우징 룰 전체를 즉각 완벽 복원**합니다.

### Step 5. 규칙 검증 및 머신러닝 파이프라인 구동
이제 모든 기초 인프라 세팅이 완료되었습니다. 터미널 혹은 주피터 노트북([`hope_housing_ml_pipeline.ipynb`](file:///c:/Users/hi/Desktop/rule-engine-playground-2/ml_predict/hope_housing_ml_pipeline.ipynb))을 열어 실행 단추를 누르면 정상적으로 돌아갑니다.

#### 1) 터미널에서 구동하는 법
```bash
# 1. 라이브 MySQL 룰 기준 엑셀 명세서 추출 및 갱신 (all_rules.xlsx 생성)
python rules_pipeline/export_rules_to_excel.py

# 2. 로컬 MySQL 연동 규칙 평가 시나리오 검사 (test_rules.py 실행)
python rules_pipeline/test_rules.py

# 3. MySQL 룰 기준 데이터셋 2,000명 동적 생성 (hope_ml_dataset.csv 생성)
python ml_predict/prep_dataset.py

# 4. 머신러닝 5대 모델 교차 훈련 및 최적 모델 저장 (best_model.pkl 생성)
python ml_predict/train.py

# 5. 모의 신청인 실시간 경쟁 합격 확률 예측 구동 (predict.py 실행)
python ml_predict/predict.py
```

#### 2) 대화형 노트북에서 구동하는 법
* [hope_housing_ml_pipeline.ipynb](file:///c:/Users/hi/Desktop/rule-engine-playground-2/ml_predict/hope_housing_ml_pipeline.ipynb) 파일을 더블 클릭하여 실행합니다.
* 노트북 최상단에 탑재된 **`📦 0-1. 필수 라이브러리 자동 설치` 셀**을 먼저 가동하여 필요한 패키지(`pymysql`, `scikit-learn` 등)를 현재 주피터 가상환경에 자동 주입한 뒤 단계별로 재미있게 분석해 볼 수 있습니다!
