import pandas as pd
import pyodbc

# =========================================================
# CSV FILE
# =========================================================

csv_path = r"D:\NEW PROJECT IMRAN\final_processed_dataset.csv"

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
# FUNCTION
# Convert Pandas/NumPy values into normal Python values
# =========================================================

def clean_value(value):

    if pd.isna(value):
        return None

    return str(value)


try:

    # =====================================================
    # READ CSV
    # =====================================================

    df = pd.read_csv(
        csv_path,
        dtype={
            "S.No.": "string",
            "Group No.": "string",
            "NAME OF GROUP MEMBERS": "string",
            "UNIVERSITY ROLL NO.": "string",
            "Name of the Supervisor": "string",
            "Project Title": "string",
            "Data_Quality_Status": "string"
        }
    )

    print("========================================")
    print("CSV READ SUCCESSFULLY")
    print("========================================")

    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    # =====================================================
    # SQL SERVER CONNECTION
    # =====================================================

    connection = pyodbc.connect(
        connection_string,
        timeout=10
    )

    cursor = connection.cursor()

    print("\nSQL Server connection successful.")

    # =====================================================
    # INSERT QUERY
    # =====================================================

    insert_query = """
        INSERT INTO dbo.ProcessedStudentData
        (
            S_No,
            Group_No,
            Student_Name,
            University_Roll_No,
            Supervisor_Name,
            Project_Title,
            Data_Quality_Status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    inserted_count = 0

    # =====================================================
    # INSERT EACH RECORD
    # =====================================================

    for index, row in df.iterrows():

        try:

            s_no = clean_value(row["S.No."])
            group_no = clean_value(row["Group No."])
            student_name = clean_value(row["NAME OF GROUP MEMBERS"])
            roll_no = clean_value(row["UNIVERSITY ROLL NO."])
            supervisor = clean_value(row["Name of the Supervisor"])
            project = clean_value(row["Project Title"])
            quality_status = clean_value(row["Data_Quality_Status"])

            cursor.execute(
                insert_query,
                s_no,
                group_no,
                student_name,
                roll_no,
                supervisor,
                project,
                quality_status
            )

            inserted_count += 1

        except Exception as row_error:

            print("\n========================================")
            print("ERROR IN ROW")
            print("========================================")

            print("CSV Row Number:", index + 2)
            print("S.No.:", row["S.No."])
            print("Group:", row["Group No."])
            print("Student:", row["NAME OF GROUP MEMBERS"])
            print("Roll No.:", row["UNIVERSITY ROLL NO."])
            print("Supervisor:", row["Name of the Supervisor"])
            print("Project:", row["Project Title"])

            print("\nError:")
            print(row_error)

            connection.rollback()

            cursor.close()
            connection.close()

            raise

    # =====================================================
    # COMMIT
    # =====================================================

    connection.commit()

    print("\n========================================")
    print("DATA INSERTED SUCCESSFULLY")
    print("========================================")

    print("Records inserted:", inserted_count)

    # =====================================================
    # VERIFY RECORD COUNT
    # =====================================================

    cursor.execute(
        "SELECT COUNT(*) FROM dbo.ProcessedStudentData"
    )

    total_records = cursor.fetchone()[0]

    print("Records currently in SQL Server:", total_records)

    # =====================================================
    # CLOSE CONNECTION
    # =====================================================

    cursor.close()
    connection.close()

    print("\nSQL Server connection closed.")

except Exception as e:

    print("\n========================================")
    print("DATA INSERT FAILED")
    print("========================================")

    print(e)