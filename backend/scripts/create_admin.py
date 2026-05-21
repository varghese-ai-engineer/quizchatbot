"""
Admin user creation script — uses PyMySQL with safe column existence checks.
Usage: docker-compose exec api python scripts/create_admin.py
"""
import os, sys, bcrypt
sys.path.insert(0, '/app')
import pymysql

MYSQL_HOST = os.getenv("DB_HOST", "mysql")
MYSQL_USER = os.getenv("DB_USER", "quizuser")
MYSQL_PASS = os.getenv("DB_PASS", "quizpass")
MYSQL_DB   = os.getenv("DB_NAME", "quizchatbot")

USERNAME = "vargheset"
EMAIL    = "vargheset@admin.local"
PASSWORD = "varghese@123"
FULLNAME = "Varghese Thomas"

pw_hash = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

conn = pymysql.connect(
    host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASS,
    database=MYSQL_DB, charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)

def column_exists(cur, table, column):
    cur.execute("""
        SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (MYSQL_DB, table, column))
    return cur.fetchone()['cnt'] > 0

with conn.cursor() as cur:
    # Add columns only if they don't already exist
    if not column_exists(cur, 'users', 'role'):
        cur.execute("ALTER TABLE users ADD COLUMN role ENUM('user','admin') NOT NULL DEFAULT 'user'")
        print("  ✓ Added column: role")

    if not column_exists(cur, 'users', 'total_credits'):
        cur.execute("ALTER TABLE users ADD COLUMN total_credits INT UNSIGNED NOT NULL DEFAULT 100")
        print("  ✓ Added column: total_credits")

    if not column_exists(cur, 'users', 'phone'):
        cur.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20) NULL")
        print("  ✓ Added column: phone")

    conn.commit()

    # Insert user without role first, then update role
    cur.execute("""
        INSERT INTO users (username, email, password, full_name, credits, language)
        VALUES (%s, %s, %s, %s, 1000, 'en')
        ON DUPLICATE KEY UPDATE password=%s, credits=1000
    """, (USERNAME, EMAIL, pw_hash, FULLNAME, pw_hash))
    conn.commit()

    # Now set admin role separately
    cur.execute("UPDATE users SET role='admin', total_credits=1000 WHERE username=%s", (USERNAME,))
    conn.commit()

    cur.execute("SELECT id, username, email, role, credits FROM users WHERE username=%s", (USERNAME,))
    row = cur.fetchone()

conn.close()

print(f"\n✅ Admin user ready:")
print(f"   ID       : {row['id']}")
print(f"   Username : {row['username']}")
print(f"   Email    : {row['email']}")
print(f"   Role     : {row['role']}")
print(f"   Credits  : {row['credits']}")
print(f"\n🔐 Login: http://localhost:8090/login.php")
print(f"   Email   : {EMAIL}")
print(f"   Password: {PASSWORD}")
