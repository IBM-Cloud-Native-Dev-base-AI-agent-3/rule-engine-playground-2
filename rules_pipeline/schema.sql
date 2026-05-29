-- ============================================================================
-- 역할: 룰 엔진 시스템의 DB 테이블 뼈대(DDL)를 생성하는 파일입니다.
-- 내용: provider, category, announcement, recruitment_target, eligibility_rule
--       5대 테이블 구조와 외래키 제약조건, 검색 성능 최적화를 위한 인덱스가 정의되어 있습니다.
-- ============================================================================

-- 1. Provider Table (e.g. SH, LH, GH, HUG)
CREATE TABLE IF NOT EXISTS provider (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- 2. Announcement Category Table (e.g. NATIONAL_RENTAL, PURCHASE_RENTAL)
CREATE TABLE IF NOT EXISTS category (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- 3. Announcement Table
CREATE TABLE IF NOT EXISTS announcement (
    id VARCHAR(100) PRIMARY KEY, -- e.g. SH_2025_NAT_01
    provider_code VARCHAR(50) NOT NULL,
    category_code VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    publish_date DATE NOT NULL,
    file_path VARCHAR(500),
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_code) REFERENCES provider(code),
    FOREIGN KEY (category_code) REFERENCES category(code)
);

-- 4. Recruitment Target Table (Sub-Products/Application Groups within an announcement)
CREATE TABLE IF NOT EXISTS recruitment_target (
    id VARCHAR(150) PRIMARY KEY, -- e.g. SH_2025_NAT_01_LT50
    announcement_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL, -- e.g. '50㎡ 이하 일반공급', '든든전세 1'
    target_type VARCHAR(100) NOT NULL, -- e.g. 'GENERAL', 'YOUTH', 'NEWLYWED'
    min_area DECIMAL(10, 2) DEFAULT 0.00,
    max_area DECIMAL(10, 2) DEFAULT 0.00,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (announcement_id) REFERENCES announcement(id) ON DELETE CASCADE
);

-- 5. Eligibility Rule Table (Easy-Rules compatible rules)
CREATE TABLE IF NOT EXISTS eligibility_rule (
    id BIGINT AUTO_INCREMENT PRIMARY KEY, -- Compatible with MySQL AUTO_INCREMENT
    target_id VARCHAR(150) NOT NULL,
    rule_name VARCHAR(255) NOT NULL, -- e.g. '주택 소유 여부 검증'
    field VARCHAR(100) NOT NULL, -- e.g. 'user.isHomeOwner', 'user.monthlyIncome'
    operator VARCHAR(50) NOT NULL, -- e.g. 'EQUAL', 'LTE', 'GTE', 'BETWEEN', 'CONTAINS_ANY'
    value TEXT NOT NULL, -- Stored as string, can be JSON representation (e.g. array, map)
    is_mandatory TINYINT DEFAULT 1, -- 1 = true (Required for eligibility), 0 = false (Scoring factor)
    rule_type VARCHAR(50) DEFAULT 'ELIGIBILITY', -- ELIGIBILITY, SCORING
    description TEXT,
    error_message VARCHAR(500), -- Error message if evaluation fails
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_id) REFERENCES recruitment_target(id) ON DELETE CASCADE
);

-- Create indices for performance
CREATE INDEX idx_announcement_provider ON announcement(provider_code);
CREATE INDEX idx_announcement_category ON announcement(category_code);
CREATE INDEX idx_recruitment_target_announcement ON recruitment_target(announcement_id);
CREATE INDEX idx_eligibility_rule_target ON eligibility_rule(target_id);
