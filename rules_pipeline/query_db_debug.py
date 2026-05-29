import sqlite3

def debug_db(db_path, schema_path, insert_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Run schema and insert
    with open(schema_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
    with open(insert_path, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())
        
    print("\n--- ANNOUNCEMENTS ---")
    cursor.execute("SELECT id, title, category_code FROM announcement")
    for r in cursor.fetchall():
        print(r)
        
    print("\n--- RECRUITMENT TARGETS ---")
    cursor.execute("SELECT id, announcement_id, name FROM recruitment_target")
    targets = cursor.fetchall()
    for r in targets:
        print(r)
        
    print("\n--- RULES COUNT PER TARGET ---")
    cursor.execute("SELECT target_id, COUNT(*) FROM eligibility_rule GROUP BY target_id")
    for r in cursor.fetchall():
        print(r)
        
    conn.close()

if __name__ == "__main__":
    debug_db("test_rules.db", "schema.sql", "insert_rules.sql")
