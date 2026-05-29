import os
import sys
import random
import re
import json
import pandas as pd

# Add rules_pipeline directory to sys.path to import db_helper
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, "../rules_pipeline"))

from db_helper import get_connection

def load_all_hope_rules():
    """
    MySQL 데이터베이스에서 희망하우징(SH_2025_HOPE_HOUSING_01)과 관련된 모든 규칙을 
    한 번에 로드하여 Target ID별로 그룹화 및 캐싱합니다. (2000번 반복 쿼리 방지)
    """
    print("MySQL 데이터베이스에서 희망하우징 룰셋 로드 및 캐싱 중...")
    try:
        conn = get_connection()
    except Exception as e:
        print(f"[오류] MySQL 연결 실패: {e}")
        sys.exit(1)
        
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT target_id, rule_name, field, operator, value, is_mandatory, rule_type, description, error_message
            FROM eligibility_rule
            WHERE target_id LIKE 'SH_2025_HOPE_HOUSING_01_%'
        """)
        
        cached_rules = {}
        for row in cursor.fetchall():
            tid = row["target_id"]
            if tid not in cached_rules:
                cached_rules[tid] = []
            cached_rules[tid].append({
                "rule_name": row["rule_name"],
                "field": row["field"],
                "operator": row["operator"],
                "value": row["value"],
                "is_mandatory": bool(row["is_mandatory"]),
                "rule_type": row["rule_type"],
                "description": row["description"],
                "error_message": row["error_message"]
            })
    conn.close()
    print(f"[성공] 총 {sum(len(v) for v in cached_rules.values())}개 규칙 캐싱 완료.")
    return cached_rules

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
        return False, f"평가 에러: {e}"

def generate_target_based_dataset(num_samples=2000, output_path="../data/processed/hope_ml_dataset.csv"):
    print(f"Generating realistic target-driven dataset of {num_samples} applicants based on MySQL rules...")
    
    random.seed(42)  # For reproducibility
    
    # 캐시된 룰셋 로드
    cached_rules = load_all_hope_rules()
    
    danjis = ["연남공공원룸텔", "희망하우징(정릉동 1036)"]
    genders = ["남성", "여성"]
    applied_priorities = [1, 2, 3]
    
    records = []
    
    for i in range(num_samples):
        # 1. Select the target room type they apply for
        applied_danji = random.choice(danjis)
        applied_gender = random.choice(genders)
        applied_priority = random.choice(applied_priorities)
        
        # 2. Basic eligibility features (Most are eligible, some ineligible to represent real errors)
        is_home_owner = random.choices([False, True], weights=[92, 8])[0]
        is_married = random.choices([False, True], weights=[97, 3])[0]
        school_location = random.choices(["서울", "기타"], weights=[92, 8])[0]
        is_graduate = random.choices([False, True], weights=[95, 5])[0]
        is_grad_suspended = random.choices([False, True], weights=[96, 4])[0]
        
        # 3. Target gender matching (Most applicants apply to matching gender rooms, some make mistakes)
        applicant_gender = random.choices([applied_gender, "남성" if applied_gender == "여성" else "여성"], weights=[95, 5])[0]
        
        # 4. Generate income/asset facts based on the priority level they applied for
        is_priority1_eligible = False
        is_recipient = False
        is_single_parent = False
        
        income_percent = 0
        total_asset = 0
        has_car = False
        car_value = 0
        
        if applied_priority == 1:
            # 1st Priority applicants submit P1 documentation
            is_priority1_eligible = random.choices([True, False], weights=[85, 15])[0] # 85% actually qualify
            if is_priority1_eligible:
                p1_type = random.choice(["recipient", "single_parent", "near_poor", "both"])
                if p1_type == "recipient":
                    is_recipient = True
                elif p1_type == "single_parent":
                    is_single_parent = True
                elif p1_type == "both":
                    is_recipient = True
                    is_single_parent = True
            # For Priority 1, income/asset screening is exempt, but let's populate them with low values
            income_percent = random.randint(20, 60)
            total_asset = random.randint(10_000_000, 80_000_000)
            
        elif applied_priority == 2:
            # 2nd Priority applicants submit family combined income/assets
            income_percent = random.randint(40, 160)  # 40% to 160% (around 100% threshold)
            total_asset = random.randint(150_000_000, 420_000_000)  # around 337M threshold
            has_car = random.choices([False, True], weights=[70, 30])[0]
            car_value = random.randint(10_000_000, 50_000_000) if has_car else 0
            
        elif applied_priority == 3:
            # 3rd Priority applicants submit individual (student-only) income/assets
            income_percent = random.randint(10, 140)  # student income (around 100% threshold)
            total_asset = random.randint(10_000_000, 140_000_000)  # student assets (around 104M threshold)
            has_car = random.choices([False, True], weights=[93, 7])[0]  # students rarely own cars
            car_value = random.randint(5_000_000, 20_000_000) if has_car else 0

        # 5. General scoring facts
        is_parents_homeless = random.choices([False, True], weights=[40, 60])[0]
        is_applicant_disabled = random.choices([False, True], weights=[95, 5])[0]
        is_parents_disabled = random.choices([False, True], weights=[90, 10])[0]
        subscription_count = random.randint(0, 30)
        
        # 6. Assemble Fact Dictionary for Rules Engine
        fact = {
            "user": {
                "gender": applicant_gender,
                "isHomeOwner": is_home_owner,
                "isMarried": is_married,
                "schoolLocation": school_location,
                "isGraduateStudent": is_graduate,
                "isGraduatedOrSuspended": is_grad_suspended,
                "incomePercent": income_percent,
                "totalAsset": total_asset,
                "carValue": car_value,
                "hasCar": has_car,
                "isPriority1Eligible": is_priority1_eligible,
                "isRecipient": is_recipient,
                "isSingleParentFamily": is_single_parent,
                "isParentsHomeless": is_parents_homeless,
                "isApplicantDisabled": is_applicant_disabled,
                "isParentsDisabled": is_parents_disabled,
                "isIncomeUnder50": (income_percent <= 50),
                "subscriptionCount": subscription_count
            }
        }
        
        # 7. Dynamically evaluate against MySQL rules
        danji_code = "YN" if applied_danji == "연남공공원룸텔" else "JR"
        gender_code = "MAL" if applied_gender == "남성" else "FEM"
        target_id = f"SH_2025_HOPE_HOUSING_01_{danji_code}_{gender_code}_PRI{applied_priority}"
        
        rules = cached_rules.get(target_id, [])
        
        passed_eligibility = True
        score = 0
        
        for rule in rules:
            if rule["rule_type"] == "ELIGIBILITY":
                passed, _ = evaluate_rule(fact, rule)
                if not passed:
                    passed_eligibility = False
            elif rule["rule_type"] == "SCORING":
                # Only score if they are eligible so far (standard rule evaluation order)
                passed, _ = evaluate_rule(fact, rule)
                if passed:
                    val_str = rule["value"]
                    if "|" in val_str:
                        pts = int(val_str.split("|")[1])
                    else:
                        pts = int(val_str)
                    score += pts
                    
        priority = applied_priority if passed_eligibility else 4
        
        # 8. Evaluate Pass/Fail outcome based on official 2025 2nd Cutlines dynamically
        passed = 0
        if priority == 1:
            passed = 1
        elif priority == 2:
            if applied_danji == "연남공공원룸텔":
                if applied_gender == "여성" and score >= 8:
                    passed = 1
                elif applied_gender == "남성" and score >= 2:
                    passed = 1
            elif applied_danji == "희망하우징(정릉동 1036)":
                if applied_gender == "여성" and score >= 8:
                    passed = 1
                elif applied_gender == "남성":
                    passed = 1  # 정릉 남성은 3순위 커트라인이므로 2순위는 자동 합격
        elif priority == 3:
            if applied_danji == "희망하우징(정릉동 1036)" and applied_gender == "남성" and score >= 0:
                passed = 1

        records.append({
            "gender": applicant_gender,
            "isHomeOwner": int(is_home_owner),
            "isMarried": int(is_married),
            "schoolLocation": school_location,
            "isGraduateStudent": int(is_graduate),
            "isGraduatedOrSuspended": int(is_grad_suspended),
            "incomePercent": income_percent,
            "totalAsset": total_asset,
            "carValue": car_value,
            "hasCar": int(has_car),
            "isPriority1Eligible": int(is_priority1_eligible),
            "isRecipient": int(is_recipient),
            "isSingleParentFamily": int(is_single_parent),
            "isParentsHomeless": int(is_parents_homeless),
            "isApplicantDisabled": int(is_applicant_disabled),
            "isParentsDisabled": int(is_parents_disabled),
            "subscriptionCount": subscription_count,
            "applied_danji": applied_danji,
            
            # Target properties applied for (essential context for the engine)
            "applied_priority": applied_priority,
            
            # Derived auditing fields (will be dropped before ML training)
            "derived_priority": priority,
            "derived_score": score,
            
            # The Label (Target)
            "Pass": passed
        })

    df = pd.DataFrame(records)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    print(f"[Success] Database-driven dataset created at: {output_path}")
    print(f"Total applicants: {len(df)}")
    print(f"Passed: {df['Pass'].sum()} ({df['Pass'].mean()*100:.1f}%)")
    print(f"Failed: {len(df) - df['Pass'].sum()} ({(1-df['Pass'].mean())*100:.1f}%)")
    
    print("\nPriority Breakdown:")
    for prio, count in df['derived_priority'].value_counts().sort_index().items():
        prio_name = {1: "1순위", 2: "2순위", 3: "3순위", 4: "부적격"}.get(prio)
        print(f"  {prio_name}: {count}명")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output = os.path.join(script_dir, "../data/processed/hope_ml_dataset.csv")
    generate_target_based_dataset(num_samples=2000, output_path=output)
