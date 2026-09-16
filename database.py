import pyodbc


# =========================================================
# SQL SERVER CONFIGURATION
# =========================================================

SERVER = r"DESKTOP-CIRBMT0\MRSQL2025"
DATABASE = "DataIngestionDB"
DRIVER = "{ODBC Driver 18 for SQL Server}"


CONNECTION_STRING = (
    f"DRIVER={DRIVER};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    try:
        connection = pyodbc.connect(CONNECTION_STRING)
        return connection

    except pyodbc.Error as error:
        print("SQL Server connection failed.")
        print("Error:", error)
        return None


# =========================================================
# TEST CONNECTION
# =========================================================

def test_connection():

    connection = get_connection()

    if connection is None:
        print("Database Connection: FAILED")
        return False

    try:

        cursor = connection.cursor()

        cursor.execute("SELECT DB_NAME()")

        database_name = cursor.fetchone()[0]

        print("Database Connection: SUCCESS")
        print("Connected Database:", database_name)

        cursor.close()
        connection.close()

        return True

    except pyodbc.Error as error:

        print("Database test failed.")
        print("Error:", error)

        connection.close()

        return False


# =========================================================
# RUN TEST
# =========================================================

if __name__ == "__main__":
    test_connection()