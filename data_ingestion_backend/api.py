import csv
import os
import pandas as pd
from functools import wraps

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from database import get_connection


api_bp = Blueprint("api", __name__)

API_KEY = os.getenv("API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
PROCESSED_FOLDER = os.path.join(BASE_DIR, "processed")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

REQUIRED_FIELDS = (
    "name",
    "email",
    "age",
    "city",
    "salary"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_value(value):
    """Convert database values into JSON-safe values."""
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def row_to_dict(cursor, row):
    """Convert SQL Server row into dictionary."""
    columns = [
        column[0]
        for column in cursor.description
    ]

    return {
        column: safe_value(value)
        for column, value in zip(columns, row)
    }


def log_api(endpoint, method, status, message):
    """Save API activity into ApiLogs table."""

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO ApiLogs
                (endpoint, method, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (
                endpoint,
                method,
                status,
                str(message)[:255]
            )
        )

        conn.commit()

    except Exception:
        # Logging failure should not break the main API response.
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


def api_key_required(view):
    """Protect API endpoints using X-API-Key."""

    @wraps(view)
    def wrapped(*args, **kwargs):

        supplied_key = request.headers.get("X-API-Key")

        if not supplied_key:

            message = "API key is required"

            log_api(
                request.path,
                request.method,
                "401",
                message
            )

            return jsonify({
                "success": False,
                "error_code": 401,
                "message": message,
                "endpoint": request.path,
                "method": request.method
            }), 401

        if supplied_key != API_KEY:

            message = "Invalid API key"

            log_api(
                request.path,
                request.method,
                "403",
                message
            )

            return jsonify({
                "success": False,
                "error_code": 403,
                "message": message,
                "endpoint": request.path,
                "method": request.method
            }), 403

        return view(*args, **kwargs)

    return wrapped


def validate_record(data):
    """Validate one employee record."""

    if not isinstance(data, dict):

        return False, "Request body must be a JSON object"

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in data
    ]

    if missing:

        return False, (
            "Missing required field(s): "
            + ", ".join(missing)
        )

    name = str(
        data.get("name", "")
    ).strip()

    email = str(
        data.get("email", "")
    ).strip()

    city = str(
        data.get("city", "")
    ).strip()

    if not name:
        return False, "Name cannot be empty"

    if not email or "@" not in email:

        return False, "A valid email is required"

    if not city:

        return False, "City cannot be empty"

    try:

        age = int(data["age"])

    except (TypeError, ValueError):

        return False, "Age must be an integer"

    if age < 1 or age > 120:

        return False, "Age must be between 1 and 120"

    try:

        salary = float(data["salary"])

    except (TypeError, ValueError):

        return False, "Salary must be a number"

    if salary < 0:

        return False, "Salary cannot be negative"

    return True, {
        "name": name,
        "email": email,
        "age": age,
        "city": city,
        "salary": salary
    }


def salary_category(salary):
    """Create salary category."""

    if salary < 40000:
        return "Low"

    if salary <= 60000:
        return "Medium"

    return "High"


def insert_record(data, cursor):
    """Insert one record into IngestionData."""

    cursor.execute(
        """
        INSERT INTO IngestionData
            (
                name,
                email,
                age,
                city,
                salary
            )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            data["email"],
            data["age"],
            data["city"],
            data["salary"]
        )
    )


# ============================================================
# ROOT
# ============================================================

@api_bp.route("/", methods=["GET"])
def root():
    """
    API root.
    ---
    tags:
      - System
    responses:
      200:
        description: API information
    """

    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API",
        "api_base_url": "/api"
    })


# ============================================================
# API HOME
# ============================================================

@api_bp.route("/api", methods=["GET"])
def api_home():
    """
    API status.
    ---
    tags:
      - System
    responses:
      200:
        description: API is running
    """

    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API is running",
        "version": "1.0.0"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@api_bp.route("/api/health", methods=["GET"])
def health():
    """
    Check API and SQL Server health.
    ---
    tags:
      - System
    responses:
      200:
        description: Health status
    """

    database_status = "connected"

    try:

        conn = get_connection()
        conn.close()

    except Exception:

        database_status = "disconnected"

    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API is running",
        "database": database_status,
        "api_base_url": "/api",
        "health_endpoint": "/api/health"
    })


# ============================================================
# SINGLE INGESTION
# ============================================================

@api_bp.route("/api/ingest", methods=["POST"])
@api_key_required
def ingest():
    """
    Ingest one employee record.
    ---
    tags:
      - Ingestion
    security:
      - ApiKeyAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - age
            - city
            - salary
          properties:
            name:
              type: string
              example: Imran Alam
            email:
              type: string
              example: imran@example.com
            age:
              type: integer
              example: 23
            city:
              type: string
              example: Noida
            salary:
              type: number
              example: 50000
    responses:
      201:
        description: Record ingested successfully
      400:
        description: Validation error
      401:
        description: API key missing
      403:
        description: Invalid API key
      409:
        description: Duplicate email
      500:
        description: Server error
    """

    data = request.get_json(silent=True)

    valid, result = validate_record(data)

    if not valid:

        log_api(
            request.path,
            request.method,
            "400",
            result
        )

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": result
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id
            FROM IngestionData
            WHERE LOWER(email) = LOWER(?)
            """,
            (result["email"],)
        )

        if cursor.fetchone():

            message = (
                "A record with this email already exists"
            )

            log_api(
                request.path,
                request.method,
                "409",
                message
            )

            return jsonify({
                "success": False,
                "error_code": 409,
                "message": message
            }), 409

        insert_record(
            result,
            cursor
        )

        conn.commit()

        cursor.execute(
            """
            SELECT TOP 1
                id,
                name,
                email,
                age,
                city,
                salary,
                created_at
            FROM IngestionData
            WHERE LOWER(email) = LOWER(?)
            ORDER BY id DESC
            """,
            (result["email"],)
        )

        record = row_to_dict(
            cursor,
            cursor.fetchone()
        )

        log_api(
            request.path,
            request.method,
            "201",
            "Record ingested successfully"
        )

        return jsonify({
            "success": True,
            "message": "Record ingested successfully",
            "data": record
        }), 201

    except Exception as error:

        if conn:
            conn.rollback()

        log_api(
            request.path,
            request.method,
            "500",
            str(error)
        )

        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "Failed to ingest record",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GET INGESTED DATA
# ============================================================

@api_bp.route("/api/data", methods=["GET"])
@api_key_required
def get_data():
    """
    Get ingested data with pagination and filters.
    ---
    tags:
      - Data
    security:
      - ApiKeyAuth: []
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 10
      - in: query
        name: city
        type: string
      - in: query
        name: search
        type: string
      - in: query
        name: min_salary
        type: number
      - in: query
        name: max_salary
        type: number
    responses:
      200:
        description: Paginated ingestion data
      400:
        description: Invalid query parameters
      401:
        description: API key missing
      403:
        description: Invalid API key
      500:
        description: Server error
    """

    try:

        page = max(
            int(request.args.get("page", 1)),
            1
        )

        limit = min(
            max(
                int(request.args.get("limit", 10)),
                1
            ),
            100
        )

    except ValueError:

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "page and limit must be integers"
        }), 400

    city = request.args.get("city")
    search = request.args.get("search")
    min_salary = request.args.get("min_salary")
    max_salary = request.args.get("max_salary")

    conditions = []
    params = []

    if city:

        conditions.append("city = ?")
        params.append(city)

    if search:

        conditions.append(
            """
            (
                name LIKE ?
                OR email LIKE ?
                OR city LIKE ?
            )
            """
        )

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value,
            search_value
        ])

    if min_salary:

        try:

            conditions.append("salary >= ?")
            params.append(float(min_salary))

        except ValueError:

            return jsonify({
                "success": False,
                "error_code": 400,
                "message": "min_salary must be a number"
            }), 400

    if max_salary:

        try:

            conditions.append("salary <= ?")
            params.append(float(max_salary))

        except ValueError:

            return jsonify({
                "success": False,
                "error_code": 400,
                "message": "max_salary must be a number"
            }), 400

    where_clause = ""

    if conditions:

        where_clause = (
            " WHERE "
            + " AND ".join(conditions)
        )

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM IngestionData
            {where_clause}
            """,
            tuple(params)
        )

        total_records = cursor.fetchone()[0]

        total_pages = (
            (total_records + limit - 1) // limit
            if total_records
            else 0
        )

        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT
                id,
                name,
                email,
                age,
                city,
                salary,
                created_at
            FROM IngestionData
            {where_clause}
            ORDER BY id DESC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
            """,
            tuple(params)
            + (offset, limit)
        )

        rows = [
            row_to_dict(cursor, row)
            for row in cursor.fetchall()
        ]

        log_api(
            request.path,
            request.method,
            "200",
            "Raw data retrieved"
        )

        return jsonify({
            "success": True,
            "count": len(rows),
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "filters": {
                "city": city,
                "search": search,
                "min_salary": min_salary,
                "max_salary": max_salary
            },
            "data": rows
        })

    except Exception as error:

        log_api(
            request.path,
            request.method,
            "500",
            str(error)
        )

        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "Failed to retrieve data",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# BATCH INGESTION
# ============================================================

@api_bp.route("/api/batch-ingest", methods=["POST"])
@api_key_required
def batch_ingest():
    """
    Ingest multiple employee records.
    ---
    tags:
      - Ingestion
    security:
      - ApiKeyAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - data
          properties:
            data:
              type: array
              items:
                type: object
                required:
                  - name
                  - email
                  - age
                  - city
                  - salary
                properties:
                  name:
                    type: string
                    example: Batch Test User 1
                  email:
                    type: string
                    example: batchtest1_2026@gmail.com
                  age:
                    type: integer
                    example: 26
                  city:
                    type: string
                    example: Noida
                  salary:
                    type: number
                    example: 47000
    responses:
      201:
        description: Batch inserted successfully
      400:
        description: Validation error
      401:
        description: API key missing
      403:
        description: Invalid API key
      409:
        description: Duplicate email
      500:
        description: Server error
    """

    payload = request.get_json(silent=True)

    if isinstance(payload, dict) and "data" in payload:

        records = payload["data"]

    else:

        records = payload

    if not isinstance(records, list) or not records:

        message = (
            "Request body must contain a non-empty JSON "
            'array or {"data": [...]}'
        )

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": message
        }), 400

    validated = []
    errors = []
    seen_emails = set()

    for index, record in enumerate(records):

        valid, result = validate_record(record)

        if not valid:

            errors.append({
                "index": index,
                "message": result
            })

            continue

        email_key = result["email"].lower()

        if email_key in seen_emails:

            errors.append({
                "index": index,
                "message": "Duplicate email inside request"
            })

            continue

        seen_emails.add(email_key)
        validated.append(result)

    if errors:

        log_api(
            request.path,
            request.method,
            "400",
            "Batch validation failed"
        )

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "Batch validation failed",
            "errors": errors
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        existing = set()

        for record in validated:

            cursor.execute(
                """
                SELECT id
                FROM IngestionData
                WHERE LOWER(email) = LOWER(?)
                """,
                (record["email"],)
            )

            if cursor.fetchone():

                existing.add(
                    record["email"].lower()
                )

        if existing:

            message = (
                "One or more email addresses already exist"
            )

            return jsonify({
                "success": False,
                "error_code": 409,
                "message": message,
                "duplicate_emails": sorted(existing)
            }), 409

        for record in validated:

            insert_record(
                record,
                cursor
            )

        conn.commit()

        message = (
            f"{len(validated)} records ingested successfully"
        )

        log_api(
            request.path,
            request.method,
            "201",
            message
        )

        return jsonify({
            "success": True,
            "message": message,
            "inserted_count": len(validated)
        }), 201

    except Exception as error:

        if conn:
            conn.rollback()

        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "Batch ingestion failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# CSV UPLOAD
# ============================================================

@api_bp.route("/api/upload-csv", methods=["POST"])
@api_key_required
def upload_csv():
    """
    Upload a CSV file and ingest records.
    ---
    tags:
      - Ingestion
    security:
      - ApiKeyAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: CSV file
    responses:
      201:
        description: CSV processed successfully
      400:
        description: Invalid CSV
      401:
        description: API key missing
      403:
        description: Invalid API key
      500:
        description: Server error
    """

    uploaded = request.files.get("file")

    if not uploaded or not uploaded.filename:

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": (
                "CSV file is required in "
                "form-data field 'file'"
            )
        }), 400

    if not uploaded.filename.lower().endswith(".csv"):

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "Only CSV files are supported"
        }), 400

    filename = secure_filename(
        uploaded.filename
    )

    if not filename:

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "Invalid filename"
        }), 400

    saved_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    uploaded.save(saved_path)

    conn = None
    cursor = None

    try:

        with open(
            saved_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as csv_file:

            reader = csv.DictReader(csv_file)
            records = list(reader)

        if not records:

            return jsonify({
                "success": False,
                "error_code": 400,
                "message": "CSV file is empty"
            }), 400

        validated = []
        errors = []

        for index, record in enumerate(records):

            valid, result = validate_record(record)

            if not valid:

                errors.append({
                    "row": index + 2,
                    "message": result
                })

            else:

                validated.append(result)

        if errors:

            return jsonify({
                "success": False,
                "error_code": 400,
                "message": "CSV validation failed",
                "errors": errors
            }), 400

        conn = get_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped_duplicates = 0

        for record in validated:

            cursor.execute(
                """
                SELECT id
                FROM IngestionData
                WHERE LOWER(email) = LOWER(?)
                """,
                (record["email"],)
            )

            if cursor.fetchone():

                skipped_duplicates += 1

                continue

            insert_record(
                record,
                cursor
            )

            inserted += 1

        conn.commit()

        message = (
            f"CSV processed: "
            f"{inserted} records inserted"
        )

        log_api(
            request.path,
            request.method,
            "201",
            message
        )

        return jsonify({
            "success": True,
            "message": "CSV processed successfully",
            "filename": filename,
            "rows_read": len(records),
            "inserted_count": inserted,
            "skipped_duplicates": skipped_duplicates
        }), 201

    except Exception as error:

        if conn:
            conn.rollback()

        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "CSV processing failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# ETL PROCESS
# ============================================================

@api_bp.route("/api/process", methods=["POST"])
@api_key_required
def process_data():
    """
    Run ETL processing from IngestionData to ProcessedData.
    ---
    tags:
      - ETL
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: ETL processing completed
      401:
        description: API key missing
      403:
        description: Invalid API key
      500:
        description: Server error
    """

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                age,
                city,
                salary
            FROM IngestionData
            ORDER BY id
            """
        )

        source_rows = cursor.fetchall()

        inserted_count = 0
        skipped_count = 0

        for (
            source_id,
            name,
            email,
            age,
            city,
            salary
        ) in source_rows:

            cursor.execute(
                """
                SELECT id
                FROM ProcessedData
                WHERE source_id = ?
                """,
                (source_id,)
            )

            if cursor.fetchone():

                skipped_count += 1

                continue

            cursor.execute(
                """
                INSERT INTO ProcessedData
                    (
                        source_id,
                        name,
                        email,
                        age,
                        city,
                        salary,
                        salary_category
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    name,
                    email,
                    age,
                    city,
                    salary,
                    salary_category(
                        float(salary)
                    )
                )
            )

            inserted_count += 1

        conn.commit()

        message = (
            "ETL processing completed successfully"
        )

        log_api(
            request.path,
            request.method,
            "200",
            message
        )

        return jsonify({
            "success": True,
            "message": message,
            "source_records": len(source_rows),
            "processed_inserted": inserted_count,
            "already_processed": skipped_count
        })

    except Exception as error:

        if conn:
            conn.rollback()

        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "ETL processing failed",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# GET PROCESSED DATA
# ============================================================

@api_bp.route("/api/processed-data", methods=["GET"])
@api_key_required
def get_processed_data():
    """Get processed data with pagination, search and filters."""

    try:
        page = max(int(request.args.get("page", 1)), 1)
        limit = min(max(int(request.args.get("limit", 10)), 1), 100)
    except ValueError:
        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "page and limit must be integers"
        }), 400

    search = request.args.get("search", "").strip()
    city = request.args.get("city", "").strip()
    category = request.args.get("salary_category", "").strip()

    conditions = []
    params = []

    if search:
        search_value = f"%{search}%"
        conditions.append("""
            (
                name LIKE ?
                OR email LIKE ?
                OR city LIKE ?
                OR salary_category LIKE ?
            )
        """)
        params.extend([search_value] * 4)

    if city:
        conditions.append("city = ?")
        params.append(city)

    if category:
        conditions.append("salary_category = ?")
        params.append(category)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT COUNT(*) FROM ProcessedData{where_clause}",
            tuple(params)
        )
        total_records = cursor.fetchone()[0]

        total_pages = (total_records + limit - 1) // limit if total_records else 0

        # Prevent an old page number from returning unrelated records after a filter.
        if total_pages and page > total_pages:
            page = total_pages

        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT
                id, source_id, name, email, age, city,
                salary, salary_category, processed_at
            FROM ProcessedData
            {where_clause}
            ORDER BY id DESC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
            """,
            tuple(params) + (offset, limit)
        )

        rows = [row_to_dict(cursor, row) for row in cursor.fetchall()]

        return jsonify({
            "success": True,
            "count": len(rows),
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "filters": {
                "search": search,
                "city": city,
                "salary_category": category
            },
            "data": rows
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "Failed to retrieve processed data",
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _read_uploaded_data(path, extension):
    """Read CSV, Excel, PDF or TXT into a DataFrame."""
    if extension == ".csv":
        return pd.read_csv(path)
    if extension in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if extension == ".pdf":
        try:
            import pdfplumber
            tables = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables() or []
                    for table in page_tables:
                        if table and len(table) >= 2:
                            tables.extend(table)
            if tables:
                header = [str(x).strip() if x is not None else "" for x in tables[0]]
                return pd.DataFrame(tables[1:], columns=header)
        except Exception:
            pass
        try:
            import pdfplumber
            text = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text.extend(page_text.splitlines())
            return _text_to_dataframe(text)
        except Exception as error:
            raise ValueError(f"PDF could not be read: {error}")
    if extension == ".txt":
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return _text_to_dataframe(f.read().splitlines())
    raise ValueError("Unsupported file format")


def _text_to_dataframe(lines):
    lines = [line.strip() for line in lines if line and line.strip()]

    if not lines:
        return pd.DataFrame()

    for separator in ("|", "\t", ";", ","):
        if separator in lines[0]:
            rows = [
                [part.strip() for part in line.split(separator)]
                for line in lines
            ]

            width = len(rows[0])

            if width > 1 and all(len(row) == width for row in rows):
                first_row = [str(value).strip().lower() for value in rows[0]]

                known_headers = {
                    "id", "name", "email", "age",
                    "city", "salary", "employee_id",
                    "email address"
                }

                if any(value in known_headers for value in first_row):
                    return pd.DataFrame(
                        rows[1:],
                        columns=rows[0]
                    )

                return pd.DataFrame(
                    rows,
                    columns=[
                        "id",
                        "name",
                        "email",
                        "age",
                        "city",
                        "salary"
                    ][:width]
                )

    return pd.DataFrame({"data": lines})


def _clean_dataframe(df):
    """Clean uploaded data without changing existing API/database logic."""

    df = df.copy()

    original_rows = len(df)

    # Clean column names
    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    # Remove completely empty rows
    df = df.dropna(how="all").copy()

    # Trim text values
    for col in df.columns:

        if df[col].dtype == "object":

            df[col] = df[col].apply(
                lambda value:
                value.strip()
                if isinstance(value, str)
                else value
            )

    # Remove duplicate rows
    before_duplicates = len(df)

    duplicate_columns = [
        col for col in df.columns
        if str(col).strip().lower() not in {"id", "employee_id"}
    ]

    if duplicate_columns:
        df = df.drop_duplicates(
            subset=duplicate_columns,
            keep="first"
        ).copy()
    else:
        df = df.drop_duplicates(
            keep="first"
        ).copy()

    duplicate_rows_removed = (
            before_duplicates - len(df)
    )

    # --------------------------------------------------------
    # Find columns
    # --------------------------------------------------------

    def find_column(names):

        for col in df.columns:

            normalized_col = (
                str(col)
                .strip()
                .lower()
                .replace("_", " ")
                .replace("-", " ")
            )

            for name in names:

                normalized_name = (
                    name
                    .strip()
                    .lower()
                    .replace("_", " ")
                    .replace("-", " ")
                )

                if normalized_col == normalized_name:
                    return col

        return None

    name_col = find_column([
        "name",
        "full name",
        "employee name"
    ])

    email_col = find_column([
        "email",
        "e-mail",
        "email address"
    ])

    age_col = find_column([
        "age"
    ])

    city_col = find_column([
        "city",
        "location"
    ])

    salary_col = find_column([
        "salary",
        "income",
        "annual salary"
    ])

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    missing_names_found = 0

    if name_col:

        name = (
            df[name_col]
            .astype("string")
            .str.strip()
        )

        missing_mask = (
            name.isna()
            |
            (name == "")
        )

        missing_names_found = int(
            missing_mask.sum()
        )

        df.loc[
            missing_mask,
            name_col
        ] = "Unknown"

        df[name_col] = (
            df[name_col]
            .astype("string")
            .str.strip()
            .str.title()
        )

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    invalid_emails_found = 0
    missing_emails_found = 0

    if email_col:

        email = (
            df[email_col]
            .astype("string")
            .str.strip()
            .str.lower()
        )

        missing_mask = (
            email.isna()
            |
            (email == "")
        )

        missing_emails_found = int(
            missing_mask.sum()
        )

        valid_mask = email.str.match(
            r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
            na=False
        )

        invalid_mask = (
            ~missing_mask
            &
            ~valid_mask
        )

        invalid_emails_found = int(
            invalid_mask.sum()
        )

        # Invalid email ko blank karo
        df.loc[
            invalid_mask,
            email_col
        ] = pd.NA

        df[email_col] = (
            df[email_col]
            .astype("string")
            .str.strip()
            .str.lower()
        )

    # --------------------------------------------------------
    # Age
    # --------------------------------------------------------

    invalid_ages_found = 0
    missing_ages_found = 0
    missing_ages_filled = 0

    if age_col:

        age = pd.to_numeric(
            df[age_col],
            errors="coerce"
        )

        missing_mask = age.isna()

        missing_ages_found = int(
            missing_mask.sum()
        )

        invalid_mask = (
            age.notna()
            &
            ~age.between(1, 120)
        )

        invalid_ages_found = int(
            invalid_mask.sum()
        )

        # Invalid age wali complete row remove karo
        if invalid_mask.any():

            df = df.loc[
                ~invalid_mask
            ].copy()

            age = age.loc[
                df.index
            ]

        # Missing age ko median se fill karo
        valid_age = age.dropna()

        if not valid_age.empty:

            fill_age = int(
                round(
                    valid_age.median()
                )
            )

        else:

            fill_age = 18

        fill_mask = age.isna()

        missing_ages_filled = int(
            fill_mask.sum()
        )

        age.loc[
            fill_mask
        ] = fill_age

        df[age_col] = (
            age
            .round()
            .astype("Int64")
        )

    # --------------------------------------------------------
    # Salary
    # --------------------------------------------------------

    invalid_salaries_found = 0
    missing_salaries_found = 0
    missing_salaries_filled = 0

    if salary_col:

        salary = pd.to_numeric(
            df[salary_col],
            errors="coerce"
        )

        missing_mask = salary.isna()

        missing_salaries_found = int(
            missing_mask.sum()
        )

        invalid_mask = (
            salary.notna()
            &
            (salary < 0)
        )

        invalid_salaries_found = int(
            invalid_mask.sum()
        )

        # Negative salary wali complete row remove karo
        if invalid_mask.any():

            df = df.loc[
                ~invalid_mask
            ].copy()

            salary = salary.loc[
                df.index
            ]

        # Missing salary ko median se fill karo
        valid_salary = salary.dropna()

        if not valid_salary.empty:

            fill_salary = float(
                valid_salary.median()
            )

        else:

            fill_salary = 0

        fill_mask = salary.isna()

        missing_salaries_filled = int(
            fill_mask.sum()
        )

        salary.loc[
            fill_mask
        ] = fill_salary

        df[salary_col] = (
            salary.round(2)
        )

    # --------------------------------------------------------
    # City
    # --------------------------------------------------------

    city_values_normalized = 0

    if city_col:

        city = (
            df[city_col]
            .astype("string")
            .str.strip()
        )

        city_map = {
            "delhi": "Delhi",
            "new delhi": "New Delhi",
            "noida": "Noida",
            "greater noida": "Greater Noida",
            "mumbai": "Mumbai",
            "bangalore": "Bangalore",
            "bengaluru": "Bangalore",
            "chennai": "Chennai",
            "kolkata": "Kolkata",
            "pune": "Pune",
            "hyderabad": "Hyderabad",
            "jaipur": "Jaipur",
            "lucknow": "Lucknow",
            "ghaziabad": "Ghaziabad",
            "gurgaon": "Gurgaon",
            "gurugram": "Gurgaon"
        }

        cleaned_city = city.apply(
            lambda value:
            city_map.get(
                str(value).strip().lower(),
                str(value).strip().title()
            )
            if pd.notna(value)
            and str(value).strip()
            else pd.NA
        )

        changed_mask = (
            city.fillna("")
            .astype(str)
            .str.strip()
            !=
            cleaned_city.fillna("")
            .astype(str)
            .str.strip()
        )

        city_values_normalized = int(
            changed_mask.sum()
        )

        mode = (
            cleaned_city
            .dropna()
            .mode()
        )

        if not mode.empty:

            city_fill = mode.iloc[0]

        else:

            city_fill = "Unknown"

        df[city_col] = (
            cleaned_city
            .fillna(city_fill)
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Remaining missing values
    # --------------------------------------------------------

    generic_missing_values_filled = 0

    for col in df.columns:

        missing_mask = df[col].isna()

        if not missing_mask.any():
            continue

        # Missing email ko Unknown se fill karo
        if col == email_col:

            fill_value = "Unknown"

        if col == name_col:

            fill_value = "Unknown"

        elif col == city_col:

            fill_value = "Unknown"

        elif col == age_col:

            values = pd.to_numeric(
                df[col],
                errors="coerce"
            ).dropna()

            fill_value = (
                int(round(values.median()))
                if not values.empty
                else 18
            )

        elif col == salary_col:

            values = pd.to_numeric(
                df[col],
                errors="coerce"
            ).dropna()

            fill_value = (
                float(values.median())
                if not values.empty
                else 0
            )

        else:

            mode = (
                df[col]
                .dropna()
                .mode()
            )

            fill_value = (
                mode.iloc[0]
                if not mode.empty
                else "Unknown"
            )

        df.loc[
            missing_mask,
            col
        ] = fill_value

        generic_missing_values_filled += int(
            missing_mask.sum()
        )

    # --------------------------------------------------------
    # Final data types
    # --------------------------------------------------------

    if age_col:

        df[age_col] = (
            pd.to_numeric(
                df[age_col],
                errors="coerce"
            )
            .round()
            .astype("Int64")
        )

    if salary_col:

        df[salary_col] = (
            pd.to_numeric(
                df[salary_col],
                errors="coerce"
            )
            .round(2)
        )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    missing_values_remaining = int(
        df.isna().sum().sum()
    )

    report = {
        "original_rows": int(original_rows),

        "final_rows": int(len(df)),

        "rows_removed": int(
            original_rows - len(df)
        ),

        "duplicate_rows_removed": int(
            duplicate_rows_removed
        ),

        "invalid_emails_found": int(
            invalid_emails_found
        ),

        "missing_emails_found": int(
            missing_emails_found
        ),

        "invalid_ages_found": int(
            invalid_ages_found
        ),

        "missing_ages_found": int(
            missing_ages_found
        ),

        "invalid_salaries_found": int(
            invalid_salaries_found
        ),

        "missing_salaries_found": int(
            missing_salaries_found
        ),

        "missing_names_found": int(
            missing_names_found
        ),

        "missing_names_filled": int(
            missing_names_found
        ),

        "missing_ages_filled": int(
            missing_ages_filled
        ),

        "missing_salaries_filled": int(
            missing_salaries_filled
        ),

        "city_values_normalized": int(
            city_values_normalized
        ),

        "normalized_cities": int(
            city_values_normalized
        ),

        "generic_missing_values_filled": int(
            generic_missing_values_filled
        ),

        "missing_values_remaining": int(
            missing_values_remaining
        )
    }

    return df, report


@api_bp.route("/api/clean-file", methods=["POST"])
@api_key_required
def clean_file():
    uploaded = request.files.get("file")

    if not uploaded or not uploaded.filename:
        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "File is required in form-data field 'file'"
        }), 400

    original_name = secure_filename(uploaded.filename)
    extension = os.path.splitext(original_name)[1].lower()
    allowed = {".csv", ".xlsx", ".xls", ".pdf", ".txt"}

    if extension not in allowed:
        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "Supported formats: CSV, Excel (.xlsx, .xls), PDF, TXT"
        }), 400

    saved_path = os.path.join(UPLOAD_FOLDER, original_name)
    uploaded.save(saved_path)

    try:
        df = _read_uploaded_data(saved_path, extension)

        if df.empty:
            return jsonify({
                "success": False,
                "error_code": 400,
                "message": "Uploaded file contains no readable data"
            }), 400

        cleaned_df, report = _clean_dataframe(df)
        base_name = os.path.splitext(original_name)[0]

        if extension == ".pdf":
            cleaned_filename = secure_filename(f"{base_name}_cleaned.csv")
            output_path = os.path.join(PROCESSED_FOLDER, cleaned_filename)
            cleaned_df.to_csv(output_path, index=False)
        elif extension == ".xls":
            cleaned_filename = secure_filename(f"{base_name}_cleaned.xlsx")
            output_path = os.path.join(PROCESSED_FOLDER, cleaned_filename)
            cleaned_df.to_excel(output_path, index=False)
        else:
            cleaned_filename = secure_filename(f"{base_name}_cleaned{extension}")
            output_path = os.path.join(PROCESSED_FOLDER, cleaned_filename)
            if extension == ".csv":
                cleaned_df.to_csv(output_path, index=False)
            elif extension == ".txt":
                cleaned_df.to_csv(output_path, index=False, sep="|")
            else:
                cleaned_df.to_excel(output_path, index=False)

        message = "File cleaned and processed successfully"
        log_api(request.path, request.method, "200", message)

        return jsonify({
            "success": True,
            "message": message,
            "file_type": extension.replace(".", "").upper(),
            "cleaned_filename": cleaned_filename,
            "download_url": f"/api/download-cleaned/{cleaned_filename}",
            "report": report
        })

    except Exception as error:
        log_api(request.path, request.method, "500", str(error))
        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "File cleaning failed",
            "error": str(error)
        }), 500


@api_bp.route("/api/download-cleaned/<path:filename>", methods=["GET"])
@api_key_required
def download_cleaned(filename):
    from flask import send_from_directory

    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "Invalid filename"
        }), 400

    full_path = os.path.join(PROCESSED_FOLDER, safe_name)
    if not os.path.isfile(full_path):
        return jsonify({
            "success": False,
            "error_code": 404,
            "message": "Cleaned file not found"
        }), 404

    return send_from_directory(
        PROCESSED_FOLDER,
        safe_name,
        as_attachment=True
    )

# ============================================================
# API LOGS
# ============================================================

@api_bp.route("/api/logs", methods=["GET"])
@api_key_required
def get_logs():
    """
    Get recent API logs.
    ---
    tags:
      - Monitoring
    security:
      - ApiKeyAuth: []
    parameters:
      - in: query
        name: limit
        type: integer
        default: 50
    responses:
      200:
        description: Recent API logs
      400:
        description: Invalid limit
      401:
        description: API key missing
      403:
        description: Invalid API key
      500:
        description: Server error
    """

    try:

        limit = min(
            max(
                int(request.args.get("limit", 50)),
                1
            ),
            200
        )

    except ValueError:

        return jsonify({
            "success": False,
            "error_code": 400,
            "message": "limit must be an integer"
        }), 400

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT TOP (?)
                id,
                endpoint,
                method,
                status,
                message,
                created_at
            FROM ApiLogs
            ORDER BY id DESC
            """,
            (limit,)
        )

        rows = [
            row_to_dict(cursor, row)
            for row in cursor.fetchall()
        ]

        return jsonify({
            "success": True,
            "count": len(rows),
            "logs": rows
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error_code": 500,
            "message": "Failed to retrieve logs",
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
































































#
#
# def _clean_dataframe(df):
#     """Clean uploaded data without changing existing API/database logic."""
#
#     df = df.copy()
#
#     original_rows = len(df)
#
#     # Clean column names
#     df.columns = [
#         str(col).strip()
#         for col in df.columns
#     ]
#
#     # Remove completely empty rows
#     df = df.dropna(how="all").copy()
#
#     # Trim text values
#     for col in df.columns:
#
#         if df[col].dtype == "object":
#
#             df[col] = df[col].apply(
#                 lambda value:
#                 value.strip()
#                 if isinstance(value, str)
#                 else value
#             )
#
#     # Remove duplicate rows
#     before_duplicates = len(df)
#
#     df = df.drop_duplicates(
#         keep="first"
#     ).copy()
#
#     duplicate_rows_removed = (
#         before_duplicates - len(df)
#     )
#
#     # --------------------------------------------------------
#     # Find columns
#     # --------------------------------------------------------
#
#     def find_column(names):
#
#         for col in df.columns:
#
#             normalized_col = (
#                 str(col)
#                 .strip()
#                 .lower()
#                 .replace("_", " ")
#                 .replace("-", " ")
#             )
#
#             for name in names:
#
#                 normalized_name = (
#                     name
#                     .strip()
#                     .lower()
#                     .replace("_", " ")
#                     .replace("-", " ")
#                 )
#
#                 if normalized_col == normalized_name:
#                     return col
#
#         return None
#
#     name_col = find_column([
#         "name",
#         "full name",
#         "employee name"
#     ])
#
#     email_col = find_column([
#         "email",
#         "e-mail",
#         "email address"
#     ])
#
#     age_col = find_column([
#         "age"
#     ])
#
#     city_col = find_column([
#         "city",
#         "location"
#     ])
#
#     salary_col = find_column([
#         "salary",
#         "income",
#         "annual salary"
#     ])
#
#     # --------------------------------------------------------
#     # Name
#     # --------------------------------------------------------
#
#     missing_names_found = 0
#
#     if name_col:
#
#         name = (
#             df[name_col]
#             .astype("string")
#             .str.strip()
#         )
#
#         missing_mask = (
#             name.isna()
#             |
#             (name == "")
#         )
#
#         missing_names_found = int(
#             missing_mask.sum()
#         )
#
#         df.loc[
#             missing_mask,
#             name_col
#         ] = "Unknown"
#
#         df[name_col] = (
#             df[name_col]
#             .astype("string")
#             .str.strip()
#             .str.title()
#         )
#
#     # --------------------------------------------------------
#     # Email
#     # --------------------------------------------------------
#
#     invalid_emails_found = 0
#     missing_emails_found = 0
#
#     if email_col:
#
#         email = (
#             df[email_col]
#             .astype("string")
#             .str.strip()
#             .str.lower()
#         )
#
#         missing_mask = (
#             email.isna()
#             |
#             (email == "")
#         )
#
#         missing_emails_found = int(
#             missing_mask.sum()
#         )
#
#         valid_mask = email.str.match(
#             r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
#             na=False
#         )
#
#         invalid_mask = (
#             ~missing_mask
#             &
#             ~valid_mask
#         )
#
#         invalid_emails_found = int(
#             invalid_mask.sum()
#         )
#
#         # Invalid email ko blank karo
#         df.loc[
#             invalid_mask,
#             email_col
#         ] = pd.NA
#
#         df[email_col] = (
#             df[email_col]
#             .astype("string")
#             .str.strip()
#             .str.lower()
#         )
#
#     # --------------------------------------------------------
#     # Age
#     # --------------------------------------------------------
#
#     invalid_ages_found = 0
#     missing_ages_found = 0
#     missing_ages_filled = 0
#
#     if age_col:
#
#         age = pd.to_numeric(
#             df[age_col],
#             errors="coerce"
#         )
#
#         missing_mask = age.isna()
#
#         missing_ages_found = int(
#             missing_mask.sum()
#         )
#
#         invalid_mask = (
#             age.notna()
#             &
#             ~age.between(1, 120)
#         )
#
#         invalid_ages_found = int(
#             invalid_mask.sum()
#         )
#
#         # Invalid age ko missing karo
#         age.loc[
#             invalid_mask
#         ] = pd.NA
#
#         valid_age = age.dropna()
#
#         if not valid_age.empty:
#
#             fill_age = int(
#                 round(
#                     valid_age.median()
#                 )
#             )
#
#         else:
#
#             fill_age = 18
#
#         fill_mask = age.isna()
#
#         missing_ages_filled = int(
#             fill_mask.sum()
#         )
#
#         age.loc[
#             fill_mask
#         ] = fill_age
#
#         df[age_col] = (
#             age
#             .round()
#             .astype("Int64")
#         )
#
#     # --------------------------------------------------------
#     # Salary
#     # --------------------------------------------------------
#
#     invalid_salaries_found = 0
#     missing_salaries_found = 0
#     missing_salaries_filled = 0
#
#     if salary_col:
#
#         salary = pd.to_numeric(
#             df[salary_col],
#             errors="coerce"
#         )
#
#         missing_mask = salary.isna()
#
#         missing_salaries_found = int(
#             missing_mask.sum()
#         )
#
#         invalid_mask = (
#             salary.notna()
#             &
#             (salary < 0)
#         )
#
#         invalid_salaries_found = int(
#             invalid_mask.sum()
#         )
#
#         # Negative salary ko missing karo
#         salary.loc[
#             invalid_mask
#         ] = pd.NA
#
#         valid_salary = salary.dropna()
#
#         if not valid_salary.empty:
#
#             fill_salary = float(
#                 valid_salary.median()
#             )
#
#         else:
#
#             fill_salary = 0
#
#         fill_mask = salary.isna()
#
#         missing_salaries_filled = int(
#             fill_mask.sum()
#         )
#
#         salary.loc[
#             fill_mask
#         ] = fill_salary
#
#         df[salary_col] = (
#             salary.round(2)
#         )
#
#     # --------------------------------------------------------
#     # City
#     # --------------------------------------------------------
#
#     city_values_normalized = 0
#
#     if city_col:
#
#         city = (
#             df[city_col]
#             .astype("string")
#             .str.strip()
#         )
#
#         city_map = {
#             "delhi": "Delhi",
#             "new delhi": "New Delhi",
#             "noida": "Noida",
#             "greater noida": "Greater Noida",
#             "mumbai": "Mumbai",
#             "bangalore": "Bangalore",
#             "bengaluru": "Bangalore",
#             "chennai": "Chennai",
#             "kolkata": "Kolkata",
#             "pune": "Pune",
#             "hyderabad": "Hyderabad",
#             "jaipur": "Jaipur",
#             "lucknow": "Lucknow",
#             "ghaziabad": "Ghaziabad",
#             "gurgaon": "Gurgaon",
#             "gurugram": "Gurgaon"
#         }
#
#         cleaned_city = city.apply(
#             lambda value:
#             city_map.get(
#                 str(value).strip().lower(),
#                 str(value).strip().title()
#             )
#             if pd.notna(value)
#             and str(value).strip()
#             else pd.NA
#         )
#
#         changed_mask = (
#             city.fillna("")
#             .astype(str)
#             .str.strip()
#             !=
#             cleaned_city.fillna("")
#             .astype(str)
#             .str.strip()
#         )
#
#         city_values_normalized = int(
#             changed_mask.sum()
#         )
#
#         mode = (
#             cleaned_city
#             .dropna()
#             .mode()
#         )
#
#         if not mode.empty:
#
#             city_fill = mode.iloc[0]
#
#         else:
#
#             city_fill = "Unknown"
#
#         df[city_col] = (
#             cleaned_city
#             .fillna(city_fill)
#             .astype("string")
#             .str.strip()
#         )
#
#     # --------------------------------------------------------
#     # Remaining missing values
#     # --------------------------------------------------------
#
#     generic_missing_values_filled = 0
#
#     for col in df.columns:
#
#         missing_mask = df[col].isna()
#
#         if not missing_mask.any():
#             continue
#
#         # Email intentionally blank rahega
#         if col == email_col:
#             continue
#
#         if col == name_col:
#
#             fill_value = "Unknown"
#
#         elif col == city_col:
#
#             fill_value = "Unknown"
#
#         elif col == age_col:
#
#             values = pd.to_numeric(
#                 df[col],
#                 errors="coerce"
#             ).dropna()
#
#             fill_value = (
#                 int(round(values.median()))
#                 if not values.empty
#                 else 18
#             )
#
#         elif col == salary_col:
#
#             values = pd.to_numeric(
#                 df[col],
#                 errors="coerce"
#             ).dropna()
#
#             fill_value = (
#                 float(values.median())
#                 if not values.empty
#                 else 0
#             )
#
#         else:
#
#             mode = (
#                 df[col]
#                 .dropna()
#                 .mode()
#             )
#
#             fill_value = (
#                 mode.iloc[0]
#                 if not mode.empty
#                 else "Unknown"
#             )
#
#         df.loc[
#             missing_mask,
#             col
#         ] = fill_value
#
#         generic_missing_values_filled += int(
#             missing_mask.sum()
#         )
#
#     # --------------------------------------------------------
#     # Final data types
#     # --------------------------------------------------------
#
#     if age_col:
#
#         df[age_col] = (
#             pd.to_numeric(
#                 df[age_col],
#                 errors="coerce"
#             )
#             .round()
#             .astype("Int64")
#         )
#
#     if salary_col:
#
#         df[salary_col] = (
#             pd.to_numeric(
#                 df[salary_col],
#                 errors="coerce"
#             )
#             .round(2)
#         )
#
#     # --------------------------------------------------------
#     # Report
#     # --------------------------------------------------------
#
#     missing_values_remaining = int(
#         df.isna().sum().sum()
#     )
#
#     report = {
#         "original_rows": int(original_rows),
#
#         "final_rows": int(len(df)),
#
#         "rows_removed": int(
#             original_rows - len(df)
#         ),
#
#         "duplicate_rows_removed": int(
#             duplicate_rows_removed
#         ),
#
#         "invalid_emails_found": int(
#             invalid_emails_found
#         ),
#
#         "missing_emails_found": int(
#             missing_emails_found
#         ),
#
#         "invalid_ages_found": int(
#             invalid_ages_found
#         ),
#
#         "missing_ages_found": int(
#             missing_ages_found
#         ),
#
#         "invalid_salaries_found": int(
#             invalid_salaries_found
#         ),
#
#         "missing_salaries_found": int(
#             missing_salaries_found
#         ),
#
#         "missing_names_found": int(
#             missing_names_found
#         ),
#
#         "missing_names_filled": int(
#             missing_names_found
#         ),
#
#         "missing_ages_filled": int(
#             missing_ages_filled
#         ),
#
#         "missing_salaries_filled": int(
#             missing_salaries_filled
#         ),
#
#         "city_values_normalized": int(
#             city_values_normalized
#         ),
#
#         "normalized_cities": int(
#             city_values_normalized
#         ),
#
#         "generic_missing_values_filled": int(
#             generic_missing_values_filled
#         ),
#
#         "missing_values_remaining": int(
#             missing_values_remaining
#         )
#     }
#
#     return df, report
