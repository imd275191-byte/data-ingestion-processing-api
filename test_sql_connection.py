import pyodbc

# =========================================================
# SQL SERVER CONFIGURATION
# =========================================================

server = r"DESKTOP-CIRBMT0\MRSQL2025"
database = "DataIngestionDB"
driver = "{ODBC Driver 18 for SQL Server}"

connection_string = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

# =========================================================
# TEST CONNECTION
# =========================================================

try:
    connection = pyodbc.connect(
        connection_string,
        timeout=10
    )

    cursor = connection.cursor()

    cursor.execute("SELECT @@SERVERNAME, DB_NAME()")

    result = cursor.fetchone()

    print("========================================")
    print("SQL SERVER CONNECTION SUCCESSFUL")
    print("========================================")
    print("Server:", result[0])
    print("Database:", result[1])

    cursor.close()
    connection.close()

except Exception as e:

    print("========================================")
    print("SQL SERVER CONNECTION FAILED")
    print("========================================")
    print(e)