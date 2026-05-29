import os
import re
import pandas as pd
from db_helper import get_connection

# ============================================================================
# 역할: 전체 규칙 데이터를 깔끔하고 가독성 높은 Excel 파일로 생성하는 스크립트입니다.
# 내용: 로컬 MySQL(rule_engine) 실시간 데이터를 연동하여 all_rules.xlsx 파일을 포맷에 맞춰 자동 빌드합니다.
# ============================================================================

def export_to_excel():
    print("MySQL 연동 Excel 내보내기 작업을 시작합니다...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Connect to live local MySQL
    try:
        conn = get_connection()
    except Exception as e:
        print(f"[오류] MySQL 데이터베이스 연결 실패: {e}")
        return
        
    # 2. Query the fully joined dataset using Pandas (한글 컬럼 매핑)
    query = """
    SELECT 
        c.name AS '대분류',
        a.title AS '공고문 제목',
        t.name AS '세부 모집 상품명',
        r.rule_name AS '규칙명',
        r.field AS '평가 변수',
        r.operator AS '연산자',
        r.value AS '기준값',
        CASE WHEN r.is_mandatory = 1 THEN '필수' ELSE '가점' END AS '구분',
        r.description AS '상세 조건 설명',
        r.error_message AS '탈락 메시지'
    FROM eligibility_rule r
    JOIN recruitment_target t ON r.target_id = t.id
    JOIN announcement a ON t.announcement_id = a.id
    JOIN category c ON a.category_code = c.code
    ORDER BY c.code, a.id, t.id, r.is_mandatory DESC, r.id;
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"[오류] 데이터 쿼리 실패: {e}")
        conn.close()
        return
        
    # 3. Post-process the DataFrame to make it extremely beautiful and professional
    df['배점'] = '-'
    
    for idx, row in df.iterrows():
        val = str(row['기준값'])
        if '|' in val:
            cond, score = val.split('|', 1)
            df.at[idx, '기준값'] = cond
            df.at[idx, '배점'] = f"{score}점"
        elif row['구분'] == '필수':
            df.at[idx, '배점'] = '필수'
            
        if row['구분'] == '가점':
            df.at[idx, '탈락 메시지'] = '-'
            
    # Reorder columns to place '배점' right after '구분' for perfect readability
    columns_order = [
        '대분류', '공고문 제목', '세부 모집 상품명', '구분', '배점',
        '규칙명', '평가 변수', '연산자', '기준값', '상세 조건 설명', '탈락 메시지'
    ]
    df = df[columns_order]
    
    # 4. Write to a beautiful Excel file with openpyxl
    excel_path = os.path.join(script_dir, "../data/processed/all_rules.xlsx")
    
    try:
        write_excel(df, excel_path)
        print(f"\n[성공] MySQL 라이브 규칙 데이터가 엑셀 파일로 생성되었습니다: {excel_path}")
    except PermissionError:
        alternative_path = os.path.join(script_dir, "../data/processed/all_rules_new.xlsx")
        print(f"\n[Warning] {excel_path} 파일이 현재 다른 프로그램에 의해 열려 있어 락(Lock) 상태입니다.")
        print(f"대신 새로운 파일 이름으로 저장합니다: {alternative_path}")
        write_excel(df, alternative_path)
        print(f"[성공] 엑셀 파일이 성공적으로 생성되었습니다: {alternative_path}")
    except Exception as e:
        print(f"[오류] 엑셀 쓰기 에러 발생: {e}")
        
    conn.close()

def write_excel(df, path):
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='전체 룰 목록')
        
        # 컬럼 자동 넓이 조절 (Autofit) 적용
        worksheet = writer.sheets['전체 룰 목록']
        for col in worksheet.columns:
            # 셀 내용 중 가장 긴 텍스트를 기준으로 열 너비 동적 설정
            max_len = 0
            for cell in col:
                val = str(cell.value or '')
                # 한글은 영어보다 가로 폭을 더 많이 차지하므로 글자 수 계산 보정
                korean_count = len(re.findall(r'[가-힣]', val))
                actual_width = len(val) + korean_count  # 한글 가중치 적용
                if actual_width > max_len:
                      max_len = actual_width
            
            col_letter = col[0].column_letter
            worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

if __name__ == "__main__":
    export_to_excel()
