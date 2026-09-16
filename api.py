from flask import Flask, jsonify, request
import pandas as pd
from database import get_connection

app = Flask(__name__)


def safe(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value


def rows(query, params=()):
    conn = get_connection()
    cur = None
    try:
        if conn is None:
            raise Exception("Database connection failed.")
        cur = conn.cursor()
        cur.execute(query, params)
        names = [c[0] for c in cur.description]
        return [{n: safe(v) for n, v in zip(names, r)} for r in cur.fetchall()]
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try:
            if conn: conn.close()
        except Exception: pass


def table_columns(table):
    data = rows("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME=?
        ORDER BY ORDINAL_POSITION
    """, (table,))
    return [x["COLUMN_NAME"] for x in data]


def find_column(columns, candidates):
    lookup = {str(x).lower(): x for x in columns}
    for c in candidates:
        if str(c).lower() in lookup:
            return lookup[str(c).lower()]
    return None


def dataset_projection():
    cols = table_columns("Datasets")
    return {
        "id": find_column(cols, ["DatasetID", "DatasetId", "ID", "Id"]),
        "name": find_column(cols, ["FileName", "Filename", "file_name", "OriginalFileName"]),
        "type": find_column(cols, ["FileType", "Filetype", "file_type"]),
        "size": find_column(cols, ["FileSize", "Filesize", "file_size"]),
        "date": find_column(cols, ["UploadedAt", "UploadDate", "CreatedAt", "CreatedDate", "Date"]),
        "status": find_column(cols, ["Status", "DatasetStatus"]),
    }


def dataset_json(r):
    return {
        "dataset_id": r.get("DatasetID") or r.get("DatasetId") or r.get("ID") or r.get("Id"),
        "file_name": r.get("FileName") or r.get("Filename") or r.get("file_name"),
        "file_type": r.get("FileType") or r.get("Filetype") or r.get("file_type"),
        "file_size": r.get("FileSize") if "FileSize" in r else r.get("file_size"),
        "uploaded_at": r.get("UploadedAt") or r.get("UploadDate") or r.get("CreatedAt") or r.get("CreatedDate"),
        "status": r.get("Status") or r.get("DatasetStatus"),
    }


# =========================================================
# ROOT API HOME
# =========================================================
@app.route("/", methods=["GET"])
def root_home():
    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API is running",
        "api_base_url": "/api",
        "health_endpoint": "/api/health"
    })


# =========================================================
# STEP 1 - API HOME
# =========================================================
@app.route("/api", methods=["GET"])
def api_home():
    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API is running",
        "version": "1.0"
    })


# =========================================================
# STEP 2 - HEALTH
# =========================================================
@app.route("/api/health", methods=["GET"])
def api_health():
    conn = None
    cur = None
    try:
        conn = get_connection()
        if conn is None:
            return jsonify({"success": False, "api": "running", "database": "disconnected"}), 500
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return jsonify({
            "success": True,
            "api": "running",
            "database": "connected",
            "database_name": "DataIngestionDB"
        })
    except Exception as e:
        return jsonify({"success": False, "api": "running", "database": "disconnected", "error": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try:
            if conn: conn.close()
        except Exception: pass


# =========================================================
# STEP 3 - ALL DATASETS
# =========================================================
@app.route("/api/datasets", methods=["GET"])
def api_get_datasets():
    try:
        data = rows("SELECT * FROM dbo.Datasets")
        return jsonify({"success": True, "count": len(data), "datasets": [dataset_json(x) for x in data]})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching datasets", "error": str(e)}), 500


# =========================================================
# STEP 14 - DATASET SEARCH
# =========================================================
@app.route("/api/datasets/search", methods=["GET"])
def api_search_datasets():
    conn = None
    cur = None
    try:
        filename = request.args.get("filename", "").strip()
        if not filename:
            return jsonify({
                "success": False,
                "message": "Please provide a filename query.",
                "example": "/api/datasets/search?filename=Data_Cleaning"
            }), 400

        conn = get_connection()
        if conn is None:
            raise Exception("Database connection failed.")

        p = dataset_projection()
        if not p["name"]:
            raise Exception("Dataset filename column not found in dbo.Datasets.")

        select = []
        if p["id"]: select.append(f"[{p['id']}] AS DatasetID")
        select.append(f"[{p['name']}] AS FileName")
        if p["type"]: select.append(f"[{p['type']}] AS FileType")
        if p["size"]: select.append(f"[{p['size']}] AS FileSize")
        if p["date"]: select.append(f"[{p['date']}] AS UploadedAt")
        if p["status"]: select.append(f"[{p['status']}] AS Status")

        cur = conn.cursor()
        cur.execute(
            f"SELECT {', '.join(select)} FROM dbo.Datasets WHERE [{p['name']}] LIKE ? ORDER BY [{p['name']}]",
            (f"%{filename}%",)
        )
        names = [c[0] for c in cur.description]
        result = [{n: safe(v) for n, v in zip(names, r)} for r in cur.fetchall()]
        return jsonify({
            "success": True,
            "query": filename,
            "count": len(result),
            "datasets": [dataset_json(x) for x in result]
        })
    except Exception as e:
        return jsonify({"success": False, "message": "Error while searching datasets", "error": str(e)}), 500
    finally:
        try:
            if cur: cur.close()
        except Exception: pass
        try:
            if conn: conn.close()
        except Exception: pass


# =========================================================
# STEP 3 SINGLE - ONE DATASET
# =========================================================
@app.route("/api/datasets/<int:dataset_id>", methods=["GET"])
def api_get_dataset(dataset_id):
    try:
        p = dataset_projection()
        if not p["id"]:
            raise Exception("Dataset ID column not found.")
        data = rows(f"SELECT * FROM dbo.Datasets WHERE [{p['id']}] = ?", (dataset_id,))
        if not data:
            return jsonify({"success": False, "message": "Dataset not found", "dataset_id": dataset_id}), 404
        return jsonify({"success": True, "dataset": dataset_json(data[0])})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching dataset", "error": str(e)}), 500


# =========================================================
# STEP 4 / STEP 13 - DATASET PROCESSED FILES
# =========================================================
@app.route("/api/datasets/<int:dataset_id>/processed-files", methods=["GET"])
def api_dataset_processed_files(dataset_id):
    try:
        data = rows("""
            SELECT ProcessedFileID, DatasetID, OriginalFileName,
                   ProcessedFileName, ProcessingType, Status,
                   OutputPath, CreatedAt
            FROM dbo.ProcessedFiles
            WHERE DatasetID = ?
            ORDER BY ProcessedFileID
        """, (dataset_id,))
        result = [{
            "processed_file_id": x.get("ProcessedFileID"),
            "dataset_id": x.get("DatasetID"),
            "original_file_name": x.get("OriginalFileName"),
            "processed_file_name": x.get("ProcessedFileName"),
            "processing_type": x.get("ProcessingType"),
            "status": x.get("Status"),
            "output_path": x.get("OutputPath"),
            "created_at": x.get("CreatedAt")
        } for x in data]
        return jsonify({"success": True, "dataset_id": dataset_id, "count": len(result), "processed_files": result})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching dataset processed files", "dataset_id": dataset_id, "error": str(e)}), 500


# =========================================================
# STEP 5 - ALL PROCESSED STUDENTS
# =========================================================
@app.route("/api/processed-students", methods=["GET"])
def api_get_processed_students():
    try:
        data = rows("""
            SELECT StudentDataID, S_No, Group_No, Student_Name,
                   University_Roll_No, Supervisor_Name, Project_Title,
                   Data_Quality_Status, CreatedAt
            FROM dbo.ProcessedStudentData
            ORDER BY StudentDataID
        """)
        result = [student_json(x) for x in data]
        return jsonify({"success": True, "count": len(result), "students": result})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching processed students", "error": str(e)}), 500


def student_json(x):
    return {
        "student_data_id": x.get("StudentDataID"),
        "s_no": x.get("S_No"),
        "group_no": x.get("Group_No"),
        "student_name": x.get("Student_Name"),
        "university_roll_no": x.get("University_Roll_No"),
        "supervisor_name": x.get("Supervisor_Name"),
        "project_title": x.get("Project_Title"),
        "data_quality_status": x.get("Data_Quality_Status"),
        "created_at": x.get("CreatedAt")
    }


# =========================================================
# STEP 6 - ONE PROCESSED STUDENT
# =========================================================
@app.route("/api/processed-students/<int:student_data_id>", methods=["GET"])
def api_get_processed_student(student_data_id):
    try:
        data = rows("""
            SELECT StudentDataID, S_No, Group_No, Student_Name,
                   University_Roll_No, Supervisor_Name, Project_Title,
                   Data_Quality_Status, CreatedAt
            FROM dbo.ProcessedStudentData
            WHERE StudentDataID = ?
        """, (student_data_id,))
        if not data:
            return jsonify({"success": False, "message": "Processed student record not found", "student_data_id": student_data_id}), 404
        return jsonify({"success": True, "student": student_json(data[0])})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching processed student", "error": str(e)}), 500


# =========================================================
# STEP 7 - SEARCH PROCESSED STUDENTS
# =========================================================
@app.route("/api/processed-students/search", methods=["GET"])
def api_search_processed_students():
    try:
        name = request.args.get("name", "").strip()
        group_no = request.args.get("group_no", "").strip()
        roll_no = request.args.get("roll_no", "").strip()

        if not name and not group_no and not roll_no:
            return jsonify({
                "success": False,
                "message": "Please provide a student name, group number, or roll number.",
                "example": "/api/processed-students/search?name=Aryan",
                "group_example": "/api/processed-students/search?group_no=G-1",
                "roll_example": "/api/processed-students/search?roll_no=2501320140035"
            }), 400

        query = """
            SELECT StudentDataID, S_No, Group_No, Student_Name,
                   University_Roll_No, Supervisor_Name, Project_Title,
                   Data_Quality_Status, CreatedAt
            FROM dbo.ProcessedStudentData
            WHERE 1 = 1
        """
        params = []

        if name:
            query += " AND Student_Name LIKE ?"
            params.append(f"%{name}%")

        # Exact group match: G-1 must NOT return G-10, G-11, etc.
        if group_no:
            query += " AND Group_No = ?"
            params.append(group_no)

        if roll_no:
            query += " AND University_Roll_No = ?"
            params.append(roll_no)

        query += " ORDER BY StudentDataID"

        data = rows(query, tuple(params))
        result = [student_json(x) for x in data]

        return jsonify({
            "success": True,
            "count": len(result),
            "filters": {
                "name": name if name else None,
                "group_no": group_no if group_no else None,
                "roll_no": roll_no if roll_no else None
            },
            "students": result
        })
    except Exception as e:
        return jsonify({"success": False, "message": "Error while searching processed students", "error": str(e)}), 500


# =========================================================
# STEP 8 - PROCESSING LOGS
# =========================================================
@app.route("/api/processing-logs/<int:dataset_id>", methods=["GET"])
def api_get_processing_logs(dataset_id):
    try:
        data = rows("""
            SELECT LogID, DatasetID, Operation, RowsBefore,
                   RowsAfter, RowsRemoved, ProcessedAt, Status
            FROM dbo.ProcessingLog
            WHERE DatasetID = ?
            ORDER BY LogID
        """, (dataset_id,))
        result = [{
            "log_id": x.get("LogID"),
            "dataset_id": x.get("DatasetID"),
            "operation": x.get("Operation"),
            "rows_before": x.get("RowsBefore"),
            "rows_after": x.get("RowsAfter"),
            "rows_removed": x.get("RowsRemoved"),
            "processed_at": x.get("ProcessedAt"),
            "status": x.get("Status")
        } for x in data]
        return jsonify({"success": True, "dataset_id": dataset_id, "count": len(result), "logs": result})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching processing logs", "dataset_id": dataset_id, "error": str(e)}), 500


# =========================================================
# STEP 9 - VALIDATION RESULTS
# =========================================================
@app.route("/api/validation-results/<int:dataset_id>", methods=["GET"])
def api_get_validation_results(dataset_id):
    try:
        # Verify dataset existence before reading validation results.
        p = dataset_projection()
        if not p["id"]:
            raise Exception("Dataset ID column not found in dbo.Datasets.")

        dataset_rows = rows(
            f"SELECT 1 FROM dbo.Datasets WHERE [{p['id']}] = ?",
            (dataset_id,)
        )
        if not dataset_rows:
            return jsonify({
                "success": False,
                "message": "Dataset not found",
                "dataset_id": dataset_id
            }), 404

        cols = table_columns("ValidationResults")
        dataset_col = find_column(cols, ["DatasetID", "DatasetId"])
        if not dataset_col:
            raise Exception("ValidationResults DatasetID column not found.")
        data = rows(f"SELECT * FROM dbo.ValidationResults WHERE [{dataset_col}] = ? ORDER BY 1", (dataset_id,))
        return jsonify({"success": True, "dataset_id": dataset_id, "count": len(data), "validation_results": data})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching validation results", "dataset_id": dataset_id, "error": str(e)}), 500


# =========================================================
# STEP 10 - ALL PROCESSED FILES
# =========================================================
@app.route("/api/processed-files", methods=["GET"])
def api_get_processed_files():
    try:
        data = rows("""
            SELECT ProcessedFileID, DatasetID, OriginalFileName,
                   ProcessedFileName, ProcessingType, Status,
                   OutputPath, CreatedAt
            FROM dbo.ProcessedFiles
            ORDER BY ProcessedFileID
        """)
        result = [processed_file_json(x) for x in data]
        return jsonify({"success": True, "count": len(result), "processed_files": result})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching processed files", "error": str(e)}), 500


def processed_file_json(x):
    return {
        "processed_file_id": x.get("ProcessedFileID"),
        "dataset_id": x.get("DatasetID"),
        "original_file_name": x.get("OriginalFileName"),
        "processed_file_name": x.get("ProcessedFileName"),
        "processing_type": x.get("ProcessingType"),
        "status": x.get("Status"),
        "output_path": x.get("OutputPath"),
        "created_at": x.get("CreatedAt")
    }


# =========================================================
# STEP 11 - ONE PROCESSED FILE
# =========================================================
@app.route("/api/processed-files/<int:processed_file_id>", methods=["GET"])
def api_get_processed_file(processed_file_id):
    try:
        data = rows("""
            SELECT ProcessedFileID, DatasetID, OriginalFileName,
                   ProcessedFileName, ProcessingType, Status,
                   OutputPath, CreatedAt
            FROM dbo.ProcessedFiles
            WHERE ProcessedFileID = ?
        """, (processed_file_id,))
        if not data:
            return jsonify({"success": False, "message": "Processed file not found", "processed_file_id": processed_file_id}), 404
        return jsonify({"success": True, "processed_file": processed_file_json(data[0])})
    except Exception as e:
        return jsonify({"success": False, "message": "Error while fetching processed file", "error": str(e)}), 500


# =========================================================
# STEP 12 - SEARCH PROCESSED FILES
# =========================================================
@app.route("/api/processed-files/search", methods=["GET"])
def api_search_processed_files():
    try:
        original = request.args.get("original_file_name")
        ptype = request.args.get("processing_type")
        status = request.args.get("status")

        conditions = []
        params = []
        if original:
            conditions.append("OriginalFileName LIKE ?")
            params.append(f"%{original}%")
        if ptype:
            conditions.append("ProcessingType = ?")
            params.append(ptype)
        if status:
            conditions.append("Status = ?")
            params.append(status)

        query = """
            SELECT ProcessedFileID, DatasetID, OriginalFileName,
                   ProcessedFileName, ProcessingType, Status,
                   OutputPath, CreatedAt
            FROM dbo.ProcessedFiles
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY ProcessedFileID"

        data = rows(query, tuple(params))
        result = [processed_file_json(x) for x in data]
        return jsonify({
            "success": True,
            "count": len(result),
            "processed_files": result,
            "filters": {
                "original_file_name": original,
                "processing_type": ptype,
                "status": status
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": "Error while searching processed files", "error": str(e)}), 500


# =========================================================
# API ERROR HANDLERS
# =========================================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "message": "API endpoint not found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"success": False, "message": "Internal API server error", "error": str(error)}), 500


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    print("=" * 60)
    print("DATA INGESTION & PROCESSING REST API")
    print("API Server : http://127.0.0.1:5051")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5051, debug=True)
