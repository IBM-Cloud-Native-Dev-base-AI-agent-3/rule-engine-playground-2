import os
import pymysql
import pymysql.constants.CLIENT

def load_env():
    """
    Simple, robust .env parser to avoid external package issues.
    Loads variables into os.environ.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, "../.env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

# Initialize environment variables
load_env()

def get_connection():
    """
    Establishes and returns a native connection to the local MySQL instance.
    Includes multi-statement support for script execution.
    """
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", 3306))
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    db = os.environ.get("DB_NAME", "rule_engine")
    
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
    )

def seed_database(schema_path, insert_path):
    """
    Seeds the local MySQL database using schema DDL and the target SQL file.
    Gracefully handles existing tables and duplicate indices.
    """
    print("\n--- Starting Local MySQL Database Seeding ---")
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Execute DDL Schema to verify tables exist
            print(f"Loading schema from: {schema_path}")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
                
            # Execute statement by statement to handle duplicate index errors gracefully
            statements = schema_sql.split(";")
            for stmt in statements:
                stmt_clean = stmt.strip()
                if not stmt_clean:
                    continue
                try:
                    cursor.execute(stmt_clean)
                    conn.commit()
                except pymysql.err.OperationalError as oe:
                    # 1061: Duplicate key name, 1050: Table already exists. Ignore these.
                    if oe.args[0] in (1061, 1050):
                        continue
                    else:
                        print(f"    [Warning] Ignored schema error on query: {stmt_clean[:50]}... Error: {oe}")
                except Exception as e:
                    print(f"    [Warning] Ignored schema error on query: {stmt_clean[:50]}... Error: {e}")
                    
            print("  [Success] Table structures and indices verified.")
            
            # 2. Run the seeding data insertion statements
            print(f"Loading and executing seed SQL from: {insert_path}")
            with open(insert_path, "r", encoding="utf-8") as f:
                insert_sql = f.read()
                
            # Multi-statement execution for insertions
            try:
                cursor.execute(insert_sql)
                conn.commit()
                print("  [Success] Seed data statements executed.")
            except Exception as e:
                print(f"  [FAIL] Database insertions encountered an error: {e}")
                raise e
            
            # 3. Print counts to verify
            cursor.execute("SELECT COUNT(*) as cnt FROM announcement")
            ann_count = cursor.fetchone()['cnt']
            cursor.execute("SELECT COUNT(*) as cnt FROM eligibility_rule")
            rule_count = cursor.fetchone()['cnt']
            print(f"\n  [Status] Live Database Stats:")
            print(f"    - Total Announcements in MySQL: {ann_count}")
            print(f"    - Total Rules in MySQL: {rule_count}")
            
    except Exception as e:
        print(f"  [FAIL] Database seeding encountered an error: {e}")
        raise e
    finally:
        conn.close()
    print("--- Seeding Phase Finished Successfully ---\n")

if __name__ == "__main__":
    # Test connection and seed if run as main
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema = os.path.join(script_dir, "schema.sql")
    insert = os.path.join(script_dir, "../data/processed/insert_rules.sql")
    seed_database(schema, insert)
