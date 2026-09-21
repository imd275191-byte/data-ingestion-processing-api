import pyodbc

server = r"DESKTOP-CIRBMT0\MRSQL2025"
database = "DataIngestionDB"

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

try:
    con = pyodbc.connect(connection_string, timeout=10)
    cur = con.cursor()

    print("\n===== DATABASE =====")
    cur.execute("SELECT DB_NAME()")
    print("Connected to:", cur.fetchone()[0])

    print("\n===== TABLES =====")
    cur.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)

    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = cur.fetchone()[0]
            print(f"{table} => {count} records")
        except Exception as e:
            print(f"{table} => ERROR: {e}")

    print("\n===== INGESTION DATA =====")
    try:
        cur.execute("""
            SELECT id, name, email, age, city, salary, created_at
            FROM IngestionData
            ORDER BY id
        """)

        rows = cur.fetchall()

        for row in rows:
            print(row)

    except Exception as e:
        print("IngestionData ERROR:", e)

    print("\n===== PROCESSED DATA =====")
    try:
        cur.execute("""
            SELECT id, source_id, name, email, age, city, salary, salary_category
            FROM ProcessedData
            ORDER BY id
        """)

        rows = cur.fetchall()

        for row in rows:
            print(row)

    except Exception as e:
        print("ProcessedData ERROR:", e)

    con.close()

except Exception as e:
    print("\nSQL SERVER CONNECTION ERROR:")
    print(e)
