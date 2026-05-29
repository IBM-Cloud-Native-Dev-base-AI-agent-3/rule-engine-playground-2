import os
import json
import re
from pypdf import PdfReader

# ============================================================================
# 역할: sh(rules) 내의 실물 PDF 파일들을 스캔하여 정형화된 DB 레코드로 변환해 주는 Python 자동화 프로그램입니다.
# 내용: [오직 희망하우징 2025년 2차 전용] 수급자 가점(3점)과 한부모가족 가점(3점)을 완벽 개별 분리하여 6점 합산을 지원합니다.
# ============================================================================

def clean_text(text):
    if not text:
        return ""
    # Normalize spaces
    return re.sub(r'\s+', ' ', text).strip()

def extract_metadata_from_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    year_match = re.search(r'(202\d)', filename)
    year = year_match.group(1) if year_match else "2025"
    
    title = filename.replace(".pdf", "")
    title = re.sub(r'^[★1_\[\]\s\-]+', '', title)
    title = re.sub(r'\([0-9_\s\-\.a-zA-Z가-힣]+\)$', '', title).strip()
    
    try:
        reader = PdfReader(pdf_path)
        first_page_text = reader.pages[0].extract_text()
        first_line = first_page_text.split('\n')[0] if first_page_text else ""
        if len(first_line) > 5 and ("모집" in first_line or "공고" in first_line):
            title = clean_text(first_line)[:100]
    except Exception as e:
        print(f"  [Warning] Could not extract PDF header text: {e}")
        
    return year, title

def generate_hope_housing_metadata():
    """
    2025년 2차 공고의 기숙사 단지(연남/정릉) * 성별(남성/여성) * 신청순위(1/2/3순위) 조합으로 
    12대 타겟군 및 청약가점 배점표를 포함한 규칙 목록을 완벽하게 자동 생성(Synthesis)합니다.
    """
    targets_metadata = []
    
    # 1. 단지 정의 (내발산 완전 배제!)
    danjis = [
        {
            "code": "YN",
            "name": "연남공공원룸텔",
            "full_name": "연남 공공원룸텔(임대)",
            "area_desc": "원룸형 1인실 13.4㎡",
            "min_area": 13.4,
            "max_area": 13.4,
            "desc": "서울특별시 마포구 성미산로 17길 79(연남동 487-35) 소재 보증금 1,090,000원 / 월임대료 145,300원"
        },
        {
            "code": "JR",
            "name": "희망하우징(정릉동 1036)",
            "full_name": "정릉 희망하우징(임대)",
            "area_desc": "원룸형 1인실 14.2㎡",
            "min_area": 14.2,
            "max_area": 14.2,
            "desc": "서울특별시 성북구 정릉로 199(정릉동 1036) 소재 보증금 1,090,000원 / 월임대료 90,900원"
        }
    ]
    
    # 2. 성별 정의
    genders = [
        {"code": "FEM", "name": "여성"},
        {"code": "MAL", "name": "남성"}
    ]
    
    # 3. 순위 정의
    priorities = [
        {
            "code": "PRI1",
            "name": "1순위",
            "desc": "수급자, 지원대상 한부모가족, 차상위계층 (소득 및 자산심사 전면 면제)"
        },
        {
            "code": "PRI2",
            "name": "2순위",
            "desc": "본인+부모 월평균 소득 100% 이하 및 부모포함 국민임대 자산 기준 적용"
        },
        {
            "code": "PRI3",
            "name": "3순위",
            "desc": "본인 단독 월평균 소득 100% 이하 및 본인 행복주택 자산 기준, 자동차 무소유 규정 적용"
        }
    ]
    
    # 4. 조합 루프 생성 (2 * 2 * 3 = 12대 타겟)
    for dj in danjis:
        for gd in genders:
            for pr in priorities:
                sub_code = f"{dj['code']}_{gd['code']}_{pr['code']}"
                target_name = f"{dj['full_name']} {gd['name']} {pr['name']}"
                target_description = f"{dj['desc']} | 대상 성별: {gd['name']} | 적용 자격 요건: {pr['desc']}"
                
                rules = []
                
                # A. 필수 자격요건 (ELIGIBILITY, is_mandatory: 1)
                rules.append({
                    "rule_name": "무주택 본인 여부",
                    "field": "user.isHomeOwner",
                    "operator": "EQUAL",
                    "value": "false",
                    "is_mandatory": 1,
                    "rule_type": "ELIGIBILITY",
                    "description": "신청자 본인이 무주택자여야 함 (주택공급에 관한 규칙 제53조 판정기준)",
                    "error_message": "신청자 본인이 주택을 소유하여 제외되었습니다."
                })
                rules.append({
                    "rule_name": "미혼 조건 검증",
                    "field": "user.isMarried",
                    "operator": "EQUAL",
                    "value": "false",
                    "is_mandatory": 1,
                    "rule_type": "ELIGIBILITY",
                    "description": "공고일 현재 신청자가 미혼(현재 혼인 상태가 아님)일 것",
                    "error_message": "본 공고는 미혼자만 신청할 수 있습니다."
                })
                rules.append({
                    "rule_name": "서울 소재 대학교 학적 검증",
                    "field": "user.schoolLocation",
                    "operator": "EQUAL",
                    "value": "서울",
                    "is_mandatory": 1,
                    "rule_type": "ELIGIBILITY",
                    "description": "서울특별시 소재 대학교(전문대 포함) 재학 또는 입학/복학예정자",
                    "error_message": "본 기숙사는 서울특별시 소재 대학교 재학생만 신청할 수 있습니다."
                })
                rules.append({
                    "rule_name": "대학원생 배제 룰",
                    "field": "user.isGraduateStudent",
                    "operator": "EQUAL",
                    "value": "false",
                    "is_mandatory": 1,
                    "rule_type": "ELIGIBILITY",
                    "description": "대학원생은 대학생으로 인정하지 않음 (신청 불가)",
                    "error_message": "본 기숙사는 대학원생의 신청을 불허합니다."
                })
                rules.append({
                    "rule_name": "졸업유예 및 수료자 배제 룰",
                    "field": "user.isGraduatedOrSuspended",
                    "operator": "EQUAL",
                    "value": "false",
                    "is_mandatory": 1,
                    "rule_type": "ELIGIBILITY",
                    "description": "졸업유예(수료)자는 대학생 기준으로 인정하지 않음",
                    "error_message": "졸업유예(수료)자는 대학생 기준에 미달하여 제외됩니다."
                })
                rules.append({
                    "rule_name": "성별 일치 여부 검증",
                    "field": "user.gender",
                    "operator": "EQUAL",
                    "value": gd['name'],
                    "is_mandatory": 1,
                    "rule_type": "ELIGIBILITY",
                    "description": f"신청 성별이 기숙사 성별 구분인 {gd['name']}과 일치할 것 (교차지원 전면 불가)",
                    "error_message": f"본 기숙사 호실은 {gd['name']} 공급 대상이므로 신청할 수 없습니다."
                })
                
                # B. 순위 전용 자격요건
                if pr['code'] == "PRI1":
                    rules.append({
                        "rule_name": "1순위 수급자 자격 입증",
                        "field": "user.isPriority1Eligible",
                        "operator": "EQUAL",
                        "value": "true",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "생계·주거·의료급여 수급자, 지원대상 한부모가족, 차상위계층 가구 (신청자 본인 또는 동일 등본상 부모 자격)",
                        "error_message": "희망하우징 1순위 자격 증빙이 확인되지 않습니다."
                    })
                elif pr['code'] == "PRI2":
                    rules.append({
                        "rule_name": "본인+부모 월평균소득 검증 (100% 이하)",
                        "field": "user.incomePercent",
                        "operator": "LTE",
                        "value": "100",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "본인과 부모의 월평균소득 합산액이 도시근로자 평균 100% 이하 (형제자매 제외, 부모이혼 시 1인만)",
                        "error_message": "본인 및 부모 합산 월평균소득 기준액(100%)을 초과하였습니다."
                    })
                    rules.append({
                        "rule_name": "본인+부모 총자산 검증 (국민임대 기준)",
                        "field": "user.totalAsset",
                        "operator": "LTE",
                        "value": "337000000",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "본인과 부모의 자산 합산액이 국민임대 기준인 3억 3,700만 원 이하",
                        "error_message": "부모 포함 총자산 보유한도(3.37억)를 초과하였습니다."
                    })
                    rules.append({
                        "rule_name": "부모포함 자동차가액 검증",
                        "field": "user.carValue",
                        "operator": "LTE",
                        "value": "45630000",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "부모 및 본인이 보유한 비영업용 자동차 개별가액 4,563만 원 이하",
                        "error_message": "보유 중인 자동차가 가액 기준 한도(4,563만 원)를 초과했습니다."
                    })
                elif pr['code'] == "PRI3":
                    rules.append({
                        "rule_name": "본인 단독 월평균소득 검증 (100% 이하)",
                        "field": "user.incomePercent",
                        "operator": "LTE",
                        "value": "100",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "신청자 본인의 월평균소득이 도시근로자 100% 이하 (1인 가구 소득 기준액 4,317,797원 이하)",
                        "error_message": "본인 소득이 기준액(100%)을 초과하였습니다."
                    })
                    rules.append({
                        "rule_name": "본인 단독 자산 검증 (행복주택 대학생 기준)",
                        "field": "user.totalAsset",
                        "operator": "LTE",
                        "value": "104000000",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "본인 단독 총자산 1억 400만 원 이하 (2025년 2차 기준)",
                        "error_message": "본인 총자산이 기준 한도액(1.04억)을 초과하였습니다."
                    })
                    rules.append({
                        "rule_name": "대학생 3순위 자동차 무소유 검증",
                        "field": "user.hasCar",
                        "operator": "EQUAL",
                        "value": "false",
                        "is_mandatory": 1,
                        "rule_type": "ELIGIBILITY",
                        "description": "신청자 본인 명의 자동차 무소유 규정 (보유 차량이 아예 없을 것)",
                        "error_message": "희망하우징 3순위 공급 대상자는 자가용 차량을 소유할 수 없습니다."
                    })
                
                # C. 가점 배점요건 (SCORING, is_mandatory: 0, value는 배점 점수)
                rules.append({
                    "rule_name": "부모 무주택 가점",
                    "field": "user.isParentsHomeless",
                    "operator": "EQUAL",
                    "value": "true|2",
                    "is_mandatory": 0,
                    "rule_type": "SCORING",
                    "description": "신청자의 부모가 무주택인 경우 2점 부여",
                    "error_message": "부모 유주택 가점 미충족"
                })
                rules.append({
                    "rule_name": "장애인 본인 가점",
                    "field": "user.isApplicantDisabled",
                    "operator": "EQUAL",
                    "value": "true|2",
                    "is_mandatory": 0,
                    "rule_type": "SCORING",
                    "description": "장애인등록증이 교부된 사람(본인)인 경우 2점 부여",
                    "error_message": "본인 장애인 가점 미충족"
                })
                rules.append({
                    "rule_name": "장애인 부모 가점",
                    "field": "user.isParentsDisabled",
                    "operator": "EQUAL",
                    "value": "true|1",
                    "is_mandatory": 0,
                    "rule_type": "SCORING",
                    "description": "신청자의 부모 중 장애인이 있는 경우 1점 부여",
                    "error_message": "부모 장애인 가점 미충족"
                })
                
                # 순위별 전용 가점 요건
                if pr['code'] == "PRI1":
                    # [사용자 지적 수용] 수급자 가점과 한부모가족 가점을 완전히 분리! 동시 충족 시 3+3=6점 획득 보장!
                    rules.append({
                        "rule_name": "수급자 가점",
                        "field": "user.isRecipient",
                        "operator": "EQUAL",
                        "value": "true|3",
                        "is_mandatory": 0,
                        "rule_type": "SCORING",
                        "description": "생계·주거·의료급여 수급자인 경우 3점 가점 부여",
                        "error_message": "수급자 가점 요건 미충족"
                    })
                    rules.append({
                        "rule_name": "지원대상 한부모가족 가점",
                        "field": "user.isSingleParentFamily",
                        "operator": "EQUAL",
                        "value": "true|3",
                        "is_mandatory": 0,
                        "rule_type": "SCORING",
                        "description": "여성가족부 지원대상 한부모가족인 경우 3점 가점 부여",
                        "error_message": "한부모가족 가점 요건 미충족"
                    })
                else:
                    rules.append({
                        "rule_name": "소득 기준 50% 이하 가점",
                        "field": "user.isIncomeUnder50",
                        "operator": "EQUAL",
                        "value": "true|3",
                        "is_mandatory": 0,
                        "rule_type": "SCORING",
                        "description": "소득수준이 해당 순위 소득 기준의 50% 이하인 경우 3점 가점 부여",
                        "error_message": "소득 50% 이하 가점 요건 미충족"
                    })
                
                # 청약저축 납입 회차 가점 보강! (다단계 가점 반영)
                rules.append({
                    "rule_name": "청약저축 가점 (24회 이상)",
                    "field": "user.subscriptionCount",
                    "operator": "GTE",
                    "value": "24|3",
                    "is_mandatory": 0,
                    "rule_type": "SCORING",
                    "description": "본인 명의 청약저축 납입 회차 24회 이상 시 3점 부여",
                    "error_message": "청약 24회 미만"
                })
                rules.append({
                    "rule_name": "청약저축 가점 (12회~24회 미만)",
                    "field": "user.subscriptionCount",
                    "operator": "BETWEEN",
                    "value": "[12, 23]|2",
                    "is_mandatory": 0,
                    "rule_type": "SCORING",
                    "description": "본인 명의 청약저축 납입 회차 12회 이상 24회 미만 시 2점 부여",
                    "error_message": "청약 12회 미만 또는 24회 이상"
                })
                rules.append({
                    "rule_name": "청약저축 가점 (6회~12회 미만)",
                    "field": "user.subscriptionCount",
                    "operator": "BETWEEN",
                    "value": "[6, 11]|1",
                    "is_mandatory": 0,
                    "rule_type": "SCORING",
                    "description": "본인 명의 청약저축 납입 회차 6회 이상 12회 미만 시 1점 부여",
                    "error_message": "청약 6회 미만 또는 12회 이상"
                })
                
                targets_metadata.append({
                    "sub_code": sub_code,
                    "name": target_name,
                    "target_type": dj['name'],
                    "min_area": dj['min_area'],
                    "max_area": dj['max_area'],
                    "description": target_description,
                    "rules": rules
                })
                
    return targets_metadata

def scan_and_generate_sql(root_dir, sql_output_path):
    print(f"Starting extraction scan in: {root_dir}")
    
    providers = [
        {"code": "SH", "name": "서울주택도시공사", "desc": "서울특별시 지방공기업으로 서울의 주택 건설 및 주거복지 전담"}
    ]
    
    categories = [
        {"code": "HOPE_HOUSING", "name": "희망하우징", "desc": "대학생의 학업 몰입을 지원하기 위해 공급하는 기숙사형 임대주택"}
    ]
    
    targets_dict = generate_hope_housing_metadata()
    
    announcements = []
    recruitment_targets = []
    eligibility_rules = []
    
    announcement_counts = {}
    
    for category_folder in os.listdir(root_dir):
        category_path = os.path.join(root_dir, category_folder)
        if not os.path.isdir(category_path):
            continue
            
        if category_folder != "희망하우징":
            continue
            
        category_code = "HOPE_HOUSING"
        
        for file in os.listdir(category_path):
            if not file.lower().endswith(".pdf"):
                continue
                
            if "커트라인" in file:
                continue
                
            pdf_path = os.path.join(category_path, file)
            print(f"Processing PDF file: {file}")
            
            year, extracted_title = extract_metadata_from_pdf(pdf_path)
            
            provider_code = "SH"
            key = f"{provider_code}_{year}_{category_code}"
            serial = announcement_counts.get(key, 0) + 1
            announcement_counts[key] = serial
            
            announcement_id = f"{provider_code}_{year}_{category_code}_{serial:02d}"
            
            announcements.append({
                "id": announcement_id,
                "provider_code": provider_code,
                "category_code": category_code,
                "title": extracted_title,
                "publish_date": f"{year}-11-27",
                "file_path": f"data/raw_pdf/{category_folder}/{file}"
            })
            
            for target in targets_dict:
                target_id = f"{announcement_id}_{target['sub_code']}"
                recruitment_targets.append({
                    "id": target_id,
                    "announcement_id": announcement_id,
                    "name": target["name"],
                    "target_type": target["target_type"],
                    "min_area": target["min_area"],
                    "max_area": target["max_area"],
                    "description": target["description"]
                })
                
                for rule in target["rules"]:
                    eligibility_rules.append({
                        "target_id": target_id,
                        "rule_name": rule["rule_name"],
                        "field": rule["field"],
                        "operator": rule["operator"],
                        "value": rule["value"],
                        "is_mandatory": rule["is_mandatory"],
                        "rule_type": rule["rule_type"],
                        "description": rule["description"],
                        "error_message": rule["error_message"]
                    })
                    
    with open(sql_output_path, "w", encoding="utf-8") as f:
        f.write("-- ============================================================================\n")
        f.write("-- 역할: 실물 공고문에서 정밀 가공해 낸 희망하우징 2025년 2차 전용 실제 룰 데이터 시드(Seed) 파일입니다.\n")
        f.write("-- 내용: [오직 희망하우징 12대 타겟 전용] 수급자/한부모가족 가점 3+3=6점 완벽 개별 분리를 반영합니다.\n")
        f.write("-- ============================================================================\n\n")
        
        # Insert Providers
        f.write("-- 1. Insert Providers\n")
        for p in providers:
            desc = p["desc"].replace("'", "''")
            f.write(f"INSERT IGNORE INTO provider (code, name, description) VALUES ('{p['code']}', '{p['name']}', '{desc}');\n")
        f.write("\n")
        
        # Insert Categories
        f.write("-- 2. Insert Categories\n")
        for c in categories:
            desc = c["desc"].replace("'", "''")
            f.write(f"INSERT IGNORE INTO category (code, name, description) VALUES ('{c['code']}', '{c['name']}', '{desc}');\n")
        f.write("\n")
        
        # Insert Announcements
        f.write("-- 3. Insert Announcements\n")
        for a in announcements:
            title = a["title"].replace("'", "''")
            file_path = a["file_path"].replace("'", "''")
            f.write(f"INSERT INTO announcement (id, provider_code, category_code, title, publish_date, file_path, status) ")
            f.write(f"VALUES ('{a['id']}', '{a['provider_code']}', '{a['category_code']}', '{title}', '{a['publish_date']}', '{file_path}', 'ACTIVE') ")
            f.write(f"ON DUPLICATE KEY UPDATE title=VALUES(title);\n")
        f.write("\n")
        
        # Insert Recruitment Targets
        f.write("-- 4. Insert Recruitment Targets\n")
        for rt in recruitment_targets:
            name = rt["name"].replace("'", "''")
            desc = rt["description"].replace("'", "''")
            f.write(f"INSERT INTO recruitment_target (id, announcement_id, name, target_type, min_area, max_area, description) ")
            f.write(f"VALUES ('{rt['id']}', '{rt['announcement_id']}', '{name}', '{rt['target_type']}', {rt['min_area']}, {rt['max_area']}, '{desc}') ")
            f.write(f"ON DUPLICATE KEY UPDATE name=VALUES(name);\n")
        f.write("\n")
        
        # Insert Eligibility Rules
        f.write("-- 5. Insert Eligibility Rules\n")
        for r in eligibility_rules:
            rule_name = r["rule_name"].replace("'", "''")
            desc = r["description"].replace("'", "''")
            err = r["error_message"].replace("'", "''")
            val = r["value"].replace("'", "''")
            f.write(f"INSERT INTO eligibility_rule (target_id, rule_name, field, operator, value, is_mandatory, rule_type, description, error_message) ")
            f.write(f"VALUES ('{r['target_id']}', '{rule_name}', '{r['field']}', '{r['operator']}', '{val}', {r['is_mandatory']}, '{r['rule_type']}', '{desc}', '{err}');\n")
            
    print(f"\n[성공] 희망하우징 12대 타겟 전용 (개별 가점 분리) 시드 SQL 작성이 완료되었습니다: {sql_output_path}")
    print(f"Total Announcements Seeded: {len(announcements)}")
    print(f"Total Sub-Targets Seeded: {len(recruitment_targets)}")
    print(f"Total Rules Seeded: {len(eligibility_rules)}")

if __name__ == "__main__":
    scan_and_generate_sql(
        root_dir=r"C:\Users\hi\Desktop\rule-engine-playground-2\data\raw_pdf",
        sql_output_path=r"C:\Users\hi\Desktop\rule-engine-playground-2\data\processed\insert_rules.sql"
    )
