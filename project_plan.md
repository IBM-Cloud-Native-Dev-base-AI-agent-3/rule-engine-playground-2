# SH/LH 공공임대주택 동적 룰 엔진 DB 설계 및 규칙 추출 프로젝트 계획서

본 프로젝트는 LH, SH, GH, HUG 등 다양한 공공주택 공급기관의 실물 모집 공고문(PDF)으로부터 복잡다단한 신청 자격요건, 입주자 선정기준, 소득 및 자산 제한 요건, 가점 조건들을 자동으로 추출하고, 이를 Java의 대표적인 경량 룰 엔진인 **Easy Rules**와 완벽하게 연동될 수 있는 **동적 데이터베이스 구조**로 정형화 및 영속화하는 것을 목표로 합니다.

---

## 1. 프로젝트 개요 및 배경

### 1.1 룰 엔진 1단계와 2단계(본 프로젝트)의 차이점
*   **1단계 (이전 아키텍처):** 단일 공고(`announcement`) 아래에 평평하게(Flat) 자격 요건 규칙(`announcement_rule`)들이 1:1로 귀속된 매우 단순한 구조였습니다. 이는 하나의 공고문에 단 한 종류의 신청 조건만 존재할 때는 유효하지만, 실제 현실의 복잡한 공고를 처리하는 데는 치명적인 한계가 있었습니다.
*   **2단계 (본 프로젝트 - 멘토링 반영):** 실제 현업 공고문 데이터를 반영하여 **"동일 공고문 내에서도 주택 전용면적, 세부 대상군(청년, 신혼부부, 일반 공급 등)에 따라 지원 자격과 소득/자산 한도가 판이하게 다르다"**는 사실을 반영했습니다. 따라서 공고와 규칙 사이에 **"세부 모집 대상 및 상품(Recruitment Target)"**이라는 중간 추상화 계층을 설계하여 현실 세계의 모든 복잡한 분기 조건을 완벽히 대응합니다.

### 1.2 비즈니스 모델 예시 (현실적인 복잡성 해결)
국민공공임대주택 공고문 하나를 예로 들면 다음과 같은 복잡한 비즈니스 로직이 한꺼번에 들어 있습니다.
*   **전용면적 50㎡ 미만 주택 지원자:** 월평균 소득이 도시근로자 평균의 **50% 이하**여야 우선 선발되며, 남은 주택에 대해 **70% 이하**인 자에게 기회가 주어집니다.
*   **전용면적 50㎡ 이상 ~ 60㎡ 이하 주택 지원자:** 청약종합저축 **6회 이상 납입** 조건이 필수이며, 월평균 소득 기준은 처음부터 **70% 이하**가 적용됩니다.
*   **든든전세주택 유형 1 vs 유형 2:** 유형 1은 무주택 조건만을 중점적으로 보며 소득 요건이 없는 반면, 유형 2는 소득 기준이 도시근로자 가구당 월평균 소득의 100%~120% 수준으로 엄격하게 제한됩니다.

이처럼 **"동일 PDF 파일에 있더라도 세부 조건이 다르면 그것은 컴퓨터 입장에서는 완전히 다른 규칙(Rule Set)이다"**라는 관점을 견지하고 본 아키텍처를 설계했습니다.

---

## 2. 동적 룰 엔진 DB 스키마 설계

어떠한 임대 기관이나 신규 상품 타입이 등장하더라도 코드 수정 없이 데이터 삽입만으로 대처할 수 있도록 고도의 정규화와 유연성을 겸비한 관계형 데이터베이스 구조를 확립했습니다.

### 2.1 데이터베이스 관계도 (Entity Relationship Diagram)

```mermaid
erJoke
erDiagram
    PROVIDER ||--o{ ANNOUNCEMENT : issues
    CATEGORY ||--o{ ANNOUNCEMENT : classifies
    ANNOUNCEMENT ||--o{ RECRUITMENT_TARGET : contains
    RECRUITMENT_TARGET ||--o{ ELIGIBILITY_RULE : defines

    PROVIDER {
        string code PK "예: 'SH', 'LH', 'GH', 'HUG'"
        string name "예: '서울주택도시공사', '한국토지주택공사'"
        string description "설명"
    }

    CATEGORY {
        string code PK "예: 'NAT_RENTAL' (국민임대), 'PUR_RENTAL' (매입임대)"
        string name "예: '국민공공임대주택', '매입임대주택'"
        string description "설명"
    }

    ANNOUNCEMENT {
        string id PK "예: 'SH_2025_NAT_01'"
        string provider_code FK "발행 기관"
        string category_code FK "공고 대분류"
        string title "공고 제목"
        date publish_date "공고 발표일"
        string file_path "PDF 파일 경로"
        string status "상태 ('ACTIVE', 'EXPIRED')"
    }

    RECRUITMENT_TARGET {
        string id PK "예: 'SH_2025_NAT_01_LT50'"
        string announcement_id FK "연관 공고 ID"
        string name "모집 대상명 (예: '50㎡ 이하 일반공급', '든든전세 1')"
        string target_type "대상 유형 ('GENERAL', 'YOUTH', 'NEWLYWED')"
        decimal min_area "최소 면적"
        decimal max_area "최대 면적"
        string description "상세 설명"
    }

    ELIGIBILITY_RULE {
        bigint id PK "자동 증가 기본키"
        string target_id FK "연관 세부 모집 대상 ID"
        string rule_name "규칙명 (예: '월평균 소득 기준액 검증')"
        string field "평가 대상 필드 (예: 'user.monthlyIncome')"
        string operator "비교 연산자 (예: 'LTE', 'BETWEEN', 'EQUAL')"
        string value "기준값 (숫자, 문자열 혹은 가산 조건을 담은 JSON)"
        boolean is_mandatory "1 = 필수 자격요건, 0 = 가점/선정기준 요건"
        string rule_type "구분 ('ELIGIBILITY' (자격), 'SCORING' (가점))"
        string description "규칙 상세 설명"
        string error_message "탈락 시 에러 메시지"
    }
```

### 2.2 각 테이블 역할 상세
1.  **기관 테이블 (`provider`)**
    *   서울의 `SH` 뿐만 아니라 전국의 `LH`, 경기도의 `GH`, 전세임대를 주관하는 `HUG`까지 기관별 규칙 차이와 데이터 출처를 유연하게 구분합니다.
2.  **대분류 테이블 (`category`)**
    *   국민공공임대주택, 매입임대주택, 도시형생활주택, 장기안심주택, 장기전세주택, 청년안심주택, 행복주택 등 주택의 법적 공급 방식에 따른 대분류 체계를 확립하여 통계 및 검색 필터링을 최적화합니다.
3.  **공고 테이블 (`announcement`)**
    *   특정 기관이 특정 일자에 발표한 고유의 공고문(PDF) 마스터 레코드를 저장합니다.
4.  **세부 모집 대상 테이블 (`recruitment_target`) 🌟가장 핵심적인 혁신 요소**
    *   하나의 공고 파일 내에 숨겨져 있는 세부 대상군(예: 청년층, 신혼부부, 고령자 등)이나 주택 크기(50㎡ 미만, 50~60㎡)별 서브 상품 정보를 분리하여 저장하는 연결고리입니다. 이 설계 덕분에 하나의 공고 안에 완전히 상반되는 소득 요건이 양립할 수 있습니다.
5.  **자격 검증 규칙 테이블 (`eligibility_rule`)**
    *   Java `Easy Rules` 엔진에 주입될 핵심 룰 데이터를 담당합니다. `field`(변수명), `operator`(연산 부호), `value`(기준값) 구조를 차용하여 규칙 엔진 로딩 시점에 코드를 수정하지 않고 런타임에 동적으로 규칙을 조합하고 바인딩할 수 있도록 보장합니다.

---

## 3. 체계적 고유 ID 명명 규칙

현업에 즉시 적용해도 겹치지 않고 데이터의 연계 계통을 한눈에 파악할 수 있도록 표준 식별자(ID) 체계를 명문화했습니다.

*   **공고 ID 생성 형식:** `{기관코드}_{연도}_{대분류코드}_{일련번호}`
    *   `SH_2025_NAT_01`: SH(서울주택도시공사)가 2025년에 공급한 국민공공임대주택(`NAT`) 계열의 1번째 공고.
    *   `LH_2026_PUR_02`: LH(한국토지주택공사)가 2026년에 공급한 매입임대주택(`PUR`) 계열의 2번째 공고.
*   **세부 모집 대상 ID 생성 형식:** `{공고ID}_{세부모집구분코드}`
    *   `SH_2025_NAT_01_LT50`: 위 공고 중 전용면적 50㎡ 미만(`LT50` - Less Than 50) 일반 공급 요건.
    *   `SH_2025_NAT_01_GE50`: 위 공고 중 전용면적 50㎡ 이상 60㎡ 이하(`GE50` - Greater or Equal 50) 공급 요건.
    *   `SH_2026_PUR_02_YTH`: 2026년 2차 매입임대 중 청년(`YTH` - Youth) 계층 자격 요건.

---

## 4. 룰 엔진(Easy Rules) 연동 및 매핑 전략

데이터베이스에 정형화된 규칙이 Java/Python 프로그램에서 어떻게 비즈니스 로직으로 실현되는지 설명합니다.

1.  **Fact 데이터 구성:**
    *   신청하려는 사용자 정보(Facts)를 Map 구조나 POJO 객체로 정의합니다.
    *   `user.age = 25`, `user.isHomeOwner = false`, `user.residence = "서울"`, `user.monthlyIncome = 2400000`, `user.householdSize = 1`
2.  **규칙 엔진 로드:**
    *   사용자가 `SH_2025_NAT_01_LT50` 모집 대상에 청약을 신청하면, 프로그램은 DB에서 `target_id = 'SH_2025_NAT_01_LT50'`인 모든 `eligibility_rule` 레코드들을 가져옵니다.
3.  **동적 룰 빌딩 및 매칭:**
    *   가져온 규칙 레코드의 `field`, `operator`, `value` 속성을 토대로 Easy Rules의 `Rule` 인스턴스를 동적으로 생성합니다.
    *   예: `operator = 'LTE'`이고 `field = 'user.incomePercent'`인 경우, 사실관계(Fact)의 `user.incomePercent` 값이 DB에 등록된 기준값(예: `50`) 이하인지 검사하는 규칙 빌더가 런타임에 체이닝되어 통과 여부를 판단합니다.
    *   동적 가산 조건(자녀 유무 등)이 필요한 자산 한도 등은 규칙 세부의 `value`에 JSON 규격(`{"base": 337000000, "child1": 371000000, "child2": 405000000}`)을 탑재하여 룰 실행부에서 파싱 처리해 엄격히 판정합니다.

---

## 5. 구현 로드맵 및 산출물

본 프로젝트의 완료를 위해 다음과 같은 단계별 유기적 연동 코드를 구축하고 검증합니다.

```
[schema.sql]            [extract_rules.py]          [insert_rules.sql]          [test_rules.py]
  (DB 구축)    ====>   (실물 PDF 규칙 추출)  ====>  (정제 데이터 인서트)  ====>  (모의 시뮬레이션 및 검증)
```

1.  **스키마 정의 (`schema.sql`):**
    *   5대 테이블 구조와 제약 조건, 성능 최적화용 인덱스를 일체 탑재하여 DB 기본 뼈대를 만듭니다.
2.  **규칙 추출 파이프라인 (`extract_rules.py`):**
    *   `sh(rules)` 폴더 산하의 10대 공급 상품군 PDF를 파싱하여 제목, 고유 메타데이터를 식별하고, 사전에 엄밀하게 설계된 각 주택 타입별 상세 검증 규칙 세트를 연결합니다.
3.  **데이터 시드 생성 (`insert_rules.sql`):**
    *   추출 파이프라인의 결과물로써 실제 현업 규칙들이 온전히 인코딩된 대규모 SQL 시드 데이터를 자동 생성합니다.
4.  **시뮬레이션 및 단위 검사 (`test_rules.py`):**
    *   구축된 SQL을 바탕으로 가상의 메모리 SQLite DB를 띄우고, 다양한 신청자 팩트(Facts) 데이터 세트들을 밀어 넣어 각 규칙 세트들이 기획 정책대로 완벽히 작동하는지 실시간 유효성 테스트를 완료하고 레포트를 출력합니다.
