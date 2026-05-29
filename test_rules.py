import sys
import sqlite3
import json
import re

# Set stdout to UTF-8 to prevent encoding errors on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# 역할: 구축된 DB 설계와 184개 규칙 데이터가 실제 규칙 엔진처럼 빈틈없이 작동하는지 사전 유효성을 자동 검증하는 코드입니다.
# 내용: [오직 희망하우징 12대 타겟 전용] 성별 불일치 결격, 대학원생 배제, 자동차 무소유, 자산 한도 등 실물 시나리오를 검증합니다.
# ============================================================================

def setup_database(db_path, schema_path, insert_path):
    print("Setting up temporary SQLite database for Hope Housing...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Execute Schema SQL
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        schema_sql = schema_sql.replace("id BIGINT AUTO_INCREMENT PRIMARY KEY", "id INTEGER PRIMARY KEY AUTOINCREMENT")
        cursor.executescript(schema_sql)
    print("  [Success] Database schema built.")
    
    # 2. Execute Insert SQL
    with open(insert_path, "r", encoding="utf-8") as f:
        insert_sql = f.read()
        insert_sql = insert_sql.replace("INSERT IGNORE INTO", "INSERT OR IGNORE INTO")
        insert_sql = insert_sql.replace("ON DUPLICATE KEY UPDATE title=VALUES(title)", "ON CONFLICT(id) DO UPDATE SET title=excluded.title")
        insert_sql = insert_sql.replace("ON DUPLICATE KEY UPDATE name=VALUES(name)", "ON CONFLICT(id) DO UPDATE SET name=excluded.name")
        cursor.executescript(insert_sql)
    print("  [Success] Seed Hope Housing rules data inserted.")
    
    conn.commit()
    return conn

def load_rules_for_target(conn, target_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT rule_name, field, operator, value, is_mandatory, rule_type, description, error_message
        FROM eligibility_rule
        WHERE target_id = ?
    """, (target_id,))
    
    rules = []
    for row in cursor.fetchall():
        rules.append({
            "rule_name": row[0],
            "field": row[1],
            "operator": row[2],
            "value": row[3],
            "is_mandatory": bool(row[4]),
            "rule_type": row[5],
            "description": row[6],
            "error_message": row[7]
        })
    return rules

def get_nested_value(data, path):
    parts = path.split('.')
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current

def evaluate_rule(fact, rule):
    field_value = get_nested_value(fact, rule["field"])
    operator = rule["operator"]
    rule_val_str = rule["value"]
    
    # 만약 SCORING 타입이고 | 가 포함되어 있으면 조건값만 분리하여 평가
    if rule.get("rule_type") == "SCORING" and "|" in rule_val_str:
        rule_val_str, _ = rule_val_str.split("|", 1)
    
    if field_value is None:
        return False, "데이터 누락"
        
    try:
        if operator == "EQUAL":
            fact_val_str = str(field_value).strip().lower()
            expected_val_str = str(rule_val_str).strip().lower()
            return fact_val_str == expected_val_str, rule["error_message"]
            
        elif operator == "LTE":
            return float(field_value) <= float(rule_val_str), rule["error_message"]
            
        elif operator == "GTE":
            return float(field_value) >= float(rule_val_str), rule["error_message"]
            
        elif operator == "BETWEEN":
            match = re.match(r'\[\s*(\d+)\s*,\s*(\d+)\s*\]', rule_val_str)
            if match:
                low, high = float(match.group(1)), float(match.group(2))
                return low <= float(field_value) <= high, rule["error_message"]
            return False, "Invalid BETWEEN format"
            
        elif operator == "CONTAINS_ANY":
            expected_list = json.loads(rule_val_str.replace("'", '"'))
            expected_list = [str(x).strip().lower() for x in expected_list]
            return str(field_value).strip().lower() in expected_list, rule["error_message"]
            
        else:
            return False, f"Unknown operator: {operator}"
    except Exception as e:
        return False, f"평가 중 에러 발생: {str(e)}"

def run_eligibility_check(applicant_name, fact, rules):
    print(f"\n==================================================")
    print(f"신청자 평가 시작: {applicant_name}")
    print(f"신청자 정보: {json.dumps(fact, ensure_ascii=False)}")
    print(f"==================================================")
    
    passed_all = True
    failed_rules = []
    scoring_points = 0
    
    for rule in rules:
        if rule["rule_type"] == "ELIGIBILITY":
            passed, err_msg = evaluate_rule(fact, rule)
            if passed:
                print(f"  [PASS - 필수] {rule['rule_name']} - 만족")
            else:
                passed_all = False
                failed_rules.append(f"{rule['rule_name']} ({err_msg})")
                print(f"  [FAIL!! - 필수탈락] {rule['rule_name']} - 미달: {err_msg}")
        elif rule["rule_type"] == "SCORING":
            # 가점 룰 평가 (배점 누적)
            passed, _ = evaluate_rule(fact, rule)
            if passed:
                val_str = rule["value"]
                if "|" in val_str:
                    pts = int(val_str.split("|")[1])
                else:
                    pts = int(val_str)
                scoring_points += pts
                print(f"  [BONUS +{pts}점] {rule['rule_name']} 충족 - 설명: {rule['description']}")
            else:
                print(f"  [ 가점 미적용 ] {rule['rule_name']} 미충족")
                
    print(f"\n>>> 최종 평가 결과: {'★자격합격★' if passed_all else '❌자격탈락❌'}")
    if passed_all:
        print(f">>> 최종 획득 가점: [ {scoring_points} 점 ] (동점자 발생 시 가점 우선순위 적용)")
    else:
        print(f">>> 부적격 사유: {', '.join(failed_rules)}")
    return passed_all, scoring_points

if __name__ == "__main__":
    db_path = ":memory:"
    schema_path = "schema.sql"
    insert_path = "insert_rules.sql"
    
    try:
        conn = setup_database(db_path, schema_path, insert_path)
        
        # ----------------------------------------------------
        # Scenario 1: 연남공공원룸텔(임대) 남성 3순위 자격 검증 (SH_2025_HOPE_HOUSING_01_YN_MAL_PRI3)
        # ----------------------------------------------------
        target_id = "SH_2025_HOPE_HOUSING_01_YN_MAL_PRI3"
        print(f"\n[Scenario 1] 타겟 ID: '{target_id}' 자격 및 가점 연산 시작...")
        rules = load_rules_for_target(conn, target_id)
        print(f"로드 완료: {len(rules)}개 규칙 (필수 자격 및 다단계 청약가점 배점표 포함)")
        
        # 1. 합격군 청년 (청약저축 GTE 24회 가점 3점, 부모 무주택 가점 2점 -> 가점 5점 획득)
        applicant_pass = {
            "user": {
                "gender": "남성",
                "isHomeOwner": False,
                "isMarried": False,
                "schoolLocation": "서울",
                "isGraduateStudent": False,
                "isGraduatedOrSuspended": False,
                "incomePercent": 80,
                "totalAsset": 95000000,
                "hasCar": False,
                # 가점 팩트
                "isParentsHomeless": True,      # 부모 무주택 (2점)
                "isApplicantDisabled": False,
                "isParentsDisabled": False,
                "isIncomeUnder50": False,
                "subscriptionCount": 25         # 청약 25회 (3점)
            }
        }
        
        # 2. 탈락군 청년 1 (여성 신청 - 성별 불일치 탈락)
        applicant_fail_gender = {
            "user": {
                "gender": "여성",               # 남성 기숙사에 여성 신청 (성별 결격)
                "isHomeOwner": False,
                "isMarried": False,
                "schoolLocation": "서울",
                "isGraduateStudent": False,
                "isGraduatedOrSuspended": False,
                "incomePercent": 80,
                "totalAsset": 95000000,
                "hasCar": False
            }
        }
        
        # 3. 탈락군 청년 2 (일반 대학원생 신청 - 대학원생 불허 탈락)
        applicant_fail_grad = {
            "user": {
                "gender": "남성",
                "isHomeOwner": False,
                "isMarried": False,
                "schoolLocation": "서울",
                "isGraduateStudent": True,      # 대학원생 (학적 결격)
                "isGraduatedOrSuspended": False,
                "incomePercent": 80,
                "totalAsset": 95000000,
                "hasCar": False
            }
        }
        
        # 4. 탈락군 청년 3 (3순위 자가용 자동차 보유 - 차량 보유 배제 탈락)
        applicant_fail_car = {
            "user": {
                "gender": "남성",
                "isHomeOwner": False,
                "isMarried": False,
                "schoolLocation": "서울",
                "isGraduateStudent": False,
                "isGraduatedOrSuspended": False,
                "incomePercent": 80,
                "totalAsset": 95000000,
                "hasCar": True                  # 자동차 보유 (차량 결격)
            }
        }
        
        run_eligibility_check("연남 남성 기숙사 합격군 청년 (가점 5점)", applicant_pass, rules)
        run_eligibility_check("연남 남성 기숙사 성별 불일치 지원자 (탈락)", applicant_fail_gender, rules)
        run_eligibility_check("연남 남성 기숙사 대학원생 지원자 (탈락)", applicant_fail_grad, rules)
        run_eligibility_check("연남 남성 기숙사 3순위 차량 보유자 (탈락)", applicant_fail_car, rules)
        
        # ----------------------------------------------------
        # Scenario 2: 정릉 희망하우징 여성 2순위 자격 검증 (SH_2025_HOPE_HOUSING_01_JR_FEM_PRI2)
        # ----------------------------------------------------
        target_id_jr = "SH_2025_HOPE_HOUSING_01_JR_FEM_PRI2"
        print(f"\n[Scenario 2] 타겟 ID: '{target_id_jr}' 자격 및 가점 연산 시작...")
        rules_jr = load_rules_for_target(conn, target_id_jr)
        print(f"로드 완료: {len(rules_jr)}개 규칙")
        
        # 2순위 자산 초과 탈락자 검증 (기준 한도: 3억 3,700만 원)
        applicant_fail_asset = {
            "user": {
                "gender": "여성",
                "isHomeOwner": False,
                "isMarried": False,
                "schoolLocation": "서울",
                "isGraduateStudent": False,
                "isGraduatedOrSuspended": False,
                "incomePercent": 90,
                "totalAsset": 340000000,       # 3.4억 (자산 결격)
                "carValue": 35000000,
                # 가점 팩트
                "isParentsHomeless": False,
                "isApplicantDisabled": False,
                "isParentsDisabled": False,
                "isIncomeUnder50": False,
                "subscriptionCount": 15         # 청약 15회 (2점 가점)
            }
        }
        
        run_eligibility_check("정릉 여성 기숙사 2순위 자산 초과 지원자 (탈락)", applicant_fail_asset, rules_jr)
        
        # ----------------------------------------------------
        # Scenario 3: 정릉 희망하우징 여성 1순위 자격 및 개별 가점 검증 (SH_2025_HOPE_HOUSING_01_JR_FEM_PRI1)
        # ----------------------------------------------------
        target_id_pri1 = "SH_2025_HOPE_HOUSING_01_JR_FEM_PRI1"
        print(f"\n[Scenario 3] 타겟 ID: '{target_id_pri1}' 자격 및 개별 가점 연산 시작...")
        rules_pri1 = load_rules_for_target(conn, target_id_pri1)
        print(f"로드 완료: {len(rules_pri1)}개 규칙")
        
        # 수급자이면서 한부모가정인 신청자 (3 + 3 = 6점 가점, 부모 무주택 2점 포함 총 8점 가점 획득)
        applicant_both = {
            "user": {
                "gender": "여성",
                "isHomeOwner": False,
                "isMarried": False,
                "schoolLocation": "서울",
                "isGraduateStudent": False,
                "isGraduatedOrSuspended": False,
                # 1순위는 별도 소득/자산 심사를 면제받으므로, 해당 값들은 1순위 자격인증 여부로 통과됨
                "isPriority1Eligible": True,
                # 가점 팩트
                "isRecipient": True,            # 수급자 가점 (3점)
                "isSingleParentFamily": True,   # 한부모가족 가점 (3점)
                "isParentsHomeless": True,      # 부모 무주택 (2점)
                "isApplicantDisabled": False,
                "isParentsDisabled": False,
                "subscriptionCount": 0          # 청약 없음
            }
        }
        
        run_eligibility_check("정릉 여성 기숙사 1순위 수급자 + 한부모가족 + 부모 무주택 충족 지원자 (합격, 가점 8점)", applicant_both, rules_pri1)
        
        conn.close()
        print("\nTemporary in-memory test database cleaned up.")
            
    except FileNotFoundError as e:
        print(f"\n[오류] 필요한 SQL 파일을 찾을 수 없습니다. extract_rules.py를 먼저 실행하여 insert_rules.sql을 만들어야 합니다: {e}")
    except Exception as e:
        print(f"\n[오류] 테스트 중 문제 발생: {e}")

