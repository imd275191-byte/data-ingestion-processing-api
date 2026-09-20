
from flask import Flask, request, jsonify
from flasgger import Swagger
import pyodbc
import re
import csv
import io
from functools import wraps
import os


app = Flask(__name__)


# ============================================================
# SWAGGER CONFIGURATION
# ============================================================

app.config["SWAGGER"] = {
    "title": "Data Ingestion & Processing REST API",
    "description": "REST API for data ingestion, validation, CSV upload, batch ingestion and ETL processing.",
    "version": "1.0.0",
    "uiversion": 3
}

swagger = Swagger(app)


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

SERVER = r"DESKTOP-CIRBMT0\MRSQL2025"
DATABASE = "DataIngestionDB"
DRIVER = "{ODBC Driver 18 for SQL Server}"

API_KEY = "demo-api-key"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)


# ============================================================
# API KEY AUTHENTICATION
# ============================================================

def require_api_key(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        provided_key = request.headers.get("X-API-Key")

        if not provided_key:

            return jsonify({
                "success": False,
                "error_code": 401,
                "message": "API key is required",
                "endpoint": request.path,
                "method": request.method
            }), 401

        if provided_key != API_KEY:

            return jsonify({
                "success": False,
                "error_code": 403,
                "message": "Invalid API key",
                "endpoint": request.path,
                "method": request.method
            }), 403

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(email):

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(pattern, email) is not None


# ============================================================
# API LOGGING
# ============================================================

def log_api(endpoint, method, status, message):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO ApiLogs
            (
                endpoint,
                method,
                status,
                message
            )
            VALUES (?, ?, ?, ?)
            """,
            endpoint,
            method,
            status,
            message
        )

        connection.commit()

    except Exception as e:

        print("Logging error:", e)

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_data(data):

    if not isinstance(data, dict):

        return False, "Each record must be a JSON object"

    required_fields = [
        "name",
        "email",
        "age",
        "city",
        "salary"
    ]

    for field in required_fields:

        if field not in data:

            return False, f"{field} is required"

    if not str(data["name"]).strip():

        return False, "Name cannot be empty"

    if not is_valid_email(str(data["email"]).strip()):

        return False, "Invalid email format"

    try:

        age = int(data["age"])

        if age < 0:

            return False, "Age cannot be negative"

    except (ValueError, TypeError):

        return False, "Age must be a valid number"

    try:

        salary = float(data["salary"])

        if salary < 0:

            return False, "Salary cannot be negative"

    except (ValueError, TypeError):

        return False, "Salary must be a valid number"

    if not str(data["city"]).strip():

        return False, "City cannot be empty"

    return True, "Valid data"


# ============================================================
# SALARY CATEGORY
# ============================================================

def get_salary_category(salary):

    salary = float(salary)

    if salary < 40000:

        return "Low"

    elif salary <= 60000:

        return "Medium"

    else:

        return "High"


# ============================================================
# GLOBAL ERROR HANDLERS
# ============================================================

@app.errorhandler(400)
def handle_bad_request(error):

    return jsonify({
        "success": False,
        "error_code": 400,
        "error": "Bad Request",
        "message": "The request is invalid or contains incorrect data",
        "endpoint": request.path,
        "method": request.method
    }), 400


@app.errorhandler(401)
def handle_unauthorized(error):

    return jsonify({
        "success": False,
        "error_code": 401,
        "error": "Unauthorized",
        "message": "Authentication is required",
        "endpoint": request.path,
        "method": request.method
    }), 401


@app.errorhandler(403)
def handle_forbidden(error):

    return jsonify({
        "success": False,
        "error_code": 403,
        "error": "Forbidden",
        "message": "You do not have permission to access this resource",
        "endpoint": request.path,
        "method": request.method
    }), 403


@app.errorhandler(404)
def handle_not_found(error):

    return jsonify({
        "success": False,
        "error_code": 404,
        "error": "Not Found",
        "message": "The requested endpoint was not found",
        "endpoint": request.path,
        "method": request.method
    }), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):

    return jsonify({
        "success": False,
        "error_code": 405,
        "error": "Method Not Allowed",
        "message": f"The {request.method} method is not allowed for this endpoint",
        "endpoint": request.path,
        "method": request.method
    }), 405


@app.errorhandler(500)
def handle_internal_server_error(error):

    return jsonify({
        "success": False,
        "error_code": 500,
        "error": "Internal Server Error",
        "message": "An unexpected error occurred on the server",
        "endpoint": request.path,
        "method": request.method
    }), 500


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():
    """
    API Home
    ---
    tags:
      - General
    responses:
      200:
        description: API is running
    """

    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API",
        "api_base_url": "/api"
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    """
    Health Check
    ---
    tags:
      - General
    responses:
      200:
        description: API health status
    """

    return jsonify({
        "success": True,
        "message": "Data Ingestion & Processing REST API is running",
        "api_base_url": "/api",
        "health_endpoint": "/api/health"
    })


# ============================================================
# SINGLE DATA INGESTION
# ============================================================

@app.route("/api/ingest", methods=["POST"])
@require_api_key
def ingest_data():
    """
    Ingest Single Record
    ---
    tags:
      - Data Ingestion
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
              example: imran@gmail.com
            age:
              type: integer
              example: 23
            city:
              type: string
              example: Noida
            salary:
              type: number
              example: 35000
    responses:
      201:
        description: Data inserted successfully
      400:
        description: Validation error
      401:
        description: API key required
      403:
        description: Invalid API key
      409:
        description: Duplicate email
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "JSON body is required",
                "endpoint": request.path,
                "method": request.method
            }), 400

        valid, message = validate_data(data)

        if not valid:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Validation Error",
                "message": message,
                "endpoint": request.path,
                "method": request.method
            }), 400

        connection = get_connection()
        cursor = connection.cursor()

        email = str(data["email"]).strip()

        cursor.execute(
            "SELECT id FROM IngestionData WHERE email = ?",
            email
        )

        existing = cursor.fetchone()

        if existing:

            log_api(
                "/api/ingest",
                "POST",
                "DUPLICATE",
                "Email already exists"
            )

            return jsonify({
                "success": False,
                "error_code": 409,
                "error": "Conflict",
                "message": "Email already exists",
                "existing_id": existing[0],
                "endpoint": request.path,
                "method": request.method
            }), 409

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
            str(data["name"]).strip(),
            email,
            int(data["age"]),
            str(data["city"]).strip(),
            float(data["salary"])
        )

        connection.commit()

        cursor.execute(
            "SELECT id FROM IngestionData WHERE email = ?",
            email
        )

        inserted = cursor.fetchone()

        if not inserted:

            raise Exception("Unable to retrieve inserted record ID")

        new_id = int(inserted[0])

        log_api(
            "/api/ingest",
            "POST",
            "SUCCESS",
            "Data inserted successfully"
        )

        return jsonify({
            "success": True,
            "message": "Data ingested successfully",
            "id": new_id
        }), 201

    except Exception as e:

        if connection:

            try:
                connection.rollback()
            except:
                pass

        print("Single ingestion error:", e)

        log_api(
            "/api/ingest",
            "POST",
            "ERROR",
            str(e)
        )

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "Database error occurred while ingesting data"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# GET RAW DATA
# ============================================================

@app.route("/api/data", methods=["GET"])
@require_api_key
def get_data():
    """
    Get Ingested Data
    ---
    tags:
      - Data Ingestion
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: limit
        in: query
        type: integer
        default: 10
      - name: city
        in: query
        type: string
      - name: min_salary
        in: query
        type: number
      - name: max_salary
        in: query
        type: number
    responses:
      200:
        description: List of ingested records
      400:
        description: Invalid query parameter
      401:
        description: API key required
      403:
        description: Invalid API key
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        try:

            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))

        except ValueError:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "page and limit must be valid integers",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if page < 1:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "page must be greater than 0",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if limit < 1:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "limit must be greater than 0",
                "endpoint": request.path,
                "method": request.method
            }), 400

        city = request.args.get("city")
        min_salary = request.args.get("min_salary")
        max_salary = request.args.get("max_salary")

        offset = (page - 1) * limit

        connection = get_connection()
        cursor = connection.cursor()

        conditions = []
        parameters = []

        min_salary_value = None
        max_salary_value = None

        if city:

            conditions.append("city = ?")
            parameters.append(city)

        if min_salary:

            try:

                min_salary_value = float(min_salary)

            except ValueError:

                return jsonify({
                    "success": False,
                    "error_code": 400,
                    "error": "Bad Request",
                    "message": "min_salary must be a valid number",
                    "endpoint": request.path,
                    "method": request.method
                }), 400

            conditions.append("salary >= ?")
            parameters.append(min_salary_value)

        if max_salary:

            try:

                max_salary_value = float(max_salary)

            except ValueError:

                return jsonify({
                    "success": False,
                    "error_code": 400,
                    "error": "Bad Request",
                    "message": "max_salary must be a valid number",
                    "endpoint": request.path,
                    "method": request.method
                }), 400

            conditions.append("salary <= ?")
            parameters.append(max_salary_value)

        if (
            min_salary_value is not None
            and max_salary_value is not None
            and min_salary_value > max_salary_value
        ):

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "min_salary cannot be greater than max_salary",
                "endpoint": request.path,
                "method": request.method
            }), 400

        where_clause = ""

        if conditions:

            where_clause = " WHERE " + " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*)
            FROM IngestionData
            {where_clause}
        """

        cursor.execute(
            count_query,
            parameters
        )

        total_records = cursor.fetchone()[0]

        total_pages = (
            (total_records + limit - 1) // limit
            if total_records > 0
            else 0
        )

        data_query = f"""
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
            ORDER BY id
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """

        cursor.execute(
            data_query,
            parameters + [offset, limit]
        )

        rows = cursor.fetchall()

        data_list = []

        for row in rows:

            data_list.append({
                "id": row.id,
                "name": row.name,
                "email": row.email,
                "age": row.age,
                "city": row.city,
                "salary": float(row.salary),
                "created_at": str(row.created_at)
            })

        return jsonify({
            "success": True,
            "page": page,
            "limit": limit,
            "count": len(data_list),
            "total_records": total_records,
            "total_pages": total_pages,
            "data": data_list
        })

    except Exception as e:

        print("Get data error:", e)

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "Database error occurred while fetching data"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# BATCH INGESTION
# ============================================================

@app.route("/api/batch-ingest", methods=["POST"])
@require_api_key
def batch_ingest():
    """
    Batch Data Ingestion
    ---
    tags:
      - Data Ingestion
    consumes:
      - application/json
    responses:
      201:
        description: Batch ingestion completed
      400:
        description: Invalid request
      401:
        description: API key required
      403:
        description: Invalid API key
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        request_data = request.get_json(silent=True)

        if request_data is None:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "JSON body is required",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if isinstance(request_data, dict):

            records = request_data.get("data")

            if records is None:

                return jsonify({
                    "success": False,
                    "error_code": 400,
                    "error": "Bad Request",
                    "message": "data must be an array",
                    "endpoint": request.path,
                    "method": request.method
                }), 400

        elif isinstance(request_data, list):

            records = request_data

        else:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "Request body must be an object containing data array or a JSON array",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if not isinstance(records, list):

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "data must be an array",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if len(records) == 0:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "data array cannot be empty",
                "endpoint": request.path,
                "method": request.method
            }), 400

        connection = get_connection()
        cursor = connection.cursor()

        inserted = []
        skipped = []
        errors = []

        for index, data in enumerate(records):

            valid, message = validate_data(data)

            if not valid:

                errors.append({
                    "index": index,
                    "message": message
                })

                continue

            email = str(data["email"]).strip()

            cursor.execute(
                "SELECT id FROM IngestionData WHERE email = ?",
                email
            )

            existing = cursor.fetchone()

            if existing:

                skipped.append({
                    "index": index,
                    "email": email,
                    "existing_id": int(existing[0]),
                    "message": "Email already exists"
                })

                continue

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
                str(data["name"]).strip(),
                email,
                int(data["age"]),
                str(data["city"]).strip(),
                float(data["salary"])
            )

            connection.commit()

            cursor.execute(
                "SELECT id FROM IngestionData WHERE email = ?",
                email
            )

            inserted_row = cursor.fetchone()

            if not inserted_row:

                raise Exception(
                    f"Unable to retrieve inserted ID for {email}"
                )

            new_id = int(inserted_row[0])

            inserted.append({
                "id": new_id,
                "email": email
            })

        log_api(
            "/api/batch-ingest",
            "POST",
            "SUCCESS",
            "Batch ingestion completed"
        )

        return jsonify({
            "success": True,
            "message": "Batch ingestion completed",
            "inserted_count": len(inserted),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors
        }), 201

    except Exception as e:

        if connection:

            try:
                connection.rollback()
            except:
                pass

        print("Batch ingestion error:", e)

        log_api(
            "/api/batch-ingest",
            "POST",
            "ERROR",
            str(e)
        )

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "Batch ingestion failed"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# CSV UPLOAD
# ============================================================

@app.route("/api/upload-csv", methods=["POST"])
@require_api_key
def upload_csv():
    """
    Upload CSV File
    ---
    tags:
      - Data Ingestion
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
    responses:
      201:
        description: CSV upload completed
      400:
        description: Invalid CSV request
      401:
        description: API key required
      403:
        description: Invalid API key
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        if "file" not in request.files:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "CSV file is required",
                "endpoint": request.path,
                "method": request.method
            }), 400

        file = request.files["file"]

        if not file.filename:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "No file selected",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if not file.filename.lower().endswith(".csv"):

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "Only CSV files are allowed",
                "endpoint": request.path,
                "method": request.method
            }), 400

        try:

            content = file.read().decode("utf-8-sig")

        except UnicodeDecodeError:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "CSV file must use UTF-8 encoding",
                "endpoint": request.path,
                "method": request.method
            }), 400

        csv_reader = csv.DictReader(
            io.StringIO(content)
        )

        required_columns = [
            "name",
            "email",
            "age",
            "city",
            "salary"
        ]

        if not csv_reader.fieldnames:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "CSV header is missing",
                "endpoint": request.path,
                "method": request.method
            }), 400

        missing_columns = [
            column
            for column in required_columns
            if column not in csv_reader.fieldnames
        ]

        if missing_columns:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "Required columns are missing",
                "missing_columns": missing_columns,
                "endpoint": request.path,
                "method": request.method
            }), 400

        connection = get_connection()
        cursor = connection.cursor()

        inserted = []
        skipped = []
        errors = []

        for index, row in enumerate(csv_reader, start=2):

            data = {
                "name": row.get("name", ""),
                "email": row.get("email", ""),
                "age": row.get("age", ""),
                "city": row.get("city", ""),
                "salary": row.get("salary", "")
            }

            valid, message = validate_data(data)

            if not valid:

                errors.append({
                    "row": index,
                    "message": message
                })

                continue

            email = str(data["email"]).strip()

            cursor.execute(
                "SELECT id FROM IngestionData WHERE email = ?",
                email
            )

            existing = cursor.fetchone()

            if existing:

                skipped.append({
                    "row": index,
                    "email": email,
                    "existing_id": int(existing[0])
                })

                continue

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
                str(data["name"]).strip(),
                email,
                int(data["age"]),
                str(data["city"]).strip(),
                float(data["salary"])
            )

            connection.commit()

            cursor.execute(
                "SELECT id FROM IngestionData WHERE email = ?",
                email
            )

            inserted_row = cursor.fetchone()

            if not inserted_row:

                raise Exception(
                    f"Unable to retrieve inserted ID for {email}"
                )

            new_id = int(inserted_row[0])

            inserted.append({
                "id": new_id,
                "email": email
            })

        log_api(
            "/api/upload-csv",
            "POST",
            "SUCCESS",
            "CSV upload completed"
        )

        return jsonify({
            "success": True,
            "message": "CSV upload completed",
            "inserted_count": len(inserted),
            "skipped_count": len(skipped),
            "error_count": len(errors),
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors
        }), 201

    except Exception as e:

        if connection:

            try:
                connection.rollback()
            except:
                pass

        print("CSV upload error:", e)

        log_api(
            "/api/upload-csv",
            "POST",
            "ERROR",
            str(e)
        )

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "CSV upload failed"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# ETL PROCESSING
# ============================================================

@app.route("/api/process", methods=["POST"])
@require_api_key
def process_data():
    """
    Process Ingested Data
    ---
    tags:
      - ETL Processing
    responses:
      200:
        description: ETL processing completed
      401:
        description: API key required
      403:
        description: Invalid API key
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

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

        rows = cursor.fetchall()

        processed_count = 0
        skipped_count = 0

        for row in rows:

            source_id = row.id

            cursor.execute(
                """
                SELECT id
                FROM ProcessedData
                WHERE source_id = ?
                """,
                source_id
            )

            already_processed = cursor.fetchone()

            if already_processed:

                skipped_count += 1
                continue

            salary_category = get_salary_category(row.salary)

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
                source_id,
                row.name,
                row.email,
                row.age,
                row.city,
                row.salary,
                salary_category
            )

            processed_count += 1

        connection.commit()

        log_api(
            "/api/process",
            "POST",
            "SUCCESS",
            "ETL processing completed"
        )

        return jsonify({
            "success": True,
            "message": "ETL processing completed",
            "processed_count": processed_count,
            "skipped_count": skipped_count
        })

    except Exception as e:

        if connection:

            try:
                connection.rollback()
            except:
                pass

        print("ETL processing error:", e)

        log_api(
            "/api/process",
            "POST",
            "ERROR",
            str(e)
        )

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "ETL processing failed"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# GET PROCESSED DATA
# ============================================================

@app.route("/api/processed-data", methods=["GET"])
@require_api_key
def get_processed_data():
    """
    Get Processed Data
    ---
    tags:
      - ETL Processing
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: limit
        in: query
        type: integer
        default: 10
      - name: city
        in: query
        type: string
      - name: salary_category
        in: query
        type: string
        enum:
          - Low
          - Medium
          - High
      - name: min_salary
        in: query
        type: number
      - name: max_salary
        in: query
        type: number
    responses:
      200:
        description: List of processed records
      400:
        description: Invalid query parameter
      401:
        description: API key required
      403:
        description: Invalid API key
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        try:

            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 10))

        except ValueError:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "page and limit must be valid integers",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if page < 1:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "page must be greater than 0",
                "endpoint": request.path,
                "method": request.method
            }), 400

        if limit < 1:

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "limit must be greater than 0",
                "endpoint": request.path,
                "method": request.method
            }), 400

        city = request.args.get("city")
        salary_category = request.args.get("salary_category")
        min_salary = request.args.get("min_salary")
        max_salary = request.args.get("max_salary")

        offset = (page - 1) * limit

        connection = get_connection()
        cursor = connection.cursor()

        conditions = []
        parameters = []

        if city:

            conditions.append("city = ?")
            parameters.append(city)

        if salary_category:

            if salary_category not in [
                "Low",
                "Medium",
                "High"
            ]:

                return jsonify({
                    "success": False,
                    "error_code": 400,
                    "error": "Bad Request",
                    "message": "salary_category must be Low, Medium or High",
                    "endpoint": request.path,
                    "method": request.method
                }), 400

            conditions.append("salary_category = ?")
            parameters.append(salary_category)

        min_salary_value = None
        max_salary_value = None

        if min_salary:

            try:

                min_salary_value = float(min_salary)

            except ValueError:

                return jsonify({
                    "success": False,
                    "error_code": 400,
                    "error": "Bad Request",
                    "message": "min_salary must be a valid number",
                    "endpoint": request.path,
                    "method": request.method
                }), 400

            conditions.append("salary >= ?")
            parameters.append(min_salary_value)

        if max_salary:

            try:

                max_salary_value = float(max_salary)

            except ValueError:

                return jsonify({
                    "success": False,
                    "error_code": 400,
                    "error": "Bad Request",
                    "message": "max_salary must be a valid number",
                    "endpoint": request.path,
                    "method": request.method
                }), 400

            conditions.append("salary <= ?")
            parameters.append(max_salary_value)

        if (
            min_salary_value is not None
            and max_salary_value is not None
            and min_salary_value > max_salary_value
        ):

            return jsonify({
                "success": False,
                "error_code": 400,
                "error": "Bad Request",
                "message": "min_salary cannot be greater than max_salary",
                "endpoint": request.path,
                "method": request.method
            }), 400

        where_clause = ""

        if conditions:

            where_clause = " WHERE " + " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*)
            FROM ProcessedData
            {where_clause}
        """

        cursor.execute(
            count_query,
            parameters
        )

        total_records = cursor.fetchone()[0]

        total_pages = (
            (total_records + limit - 1) // limit
            if total_records > 0
            else 0
        )

        data_query = f"""
            SELECT
                id,
                source_id,
                name,
                email,
                age,
                city,
                salary,
                salary_category,
                processed_at
            FROM ProcessedData
            {where_clause}
            ORDER BY id
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """

        cursor.execute(
            data_query,
            parameters + [offset, limit]
        )

        rows = cursor.fetchall()

        data_list = []

        for row in rows:

            data_list.append({
                "id": row.id,
                "source_id": row.source_id,
                "name": row.name,
                "email": row.email,
                "age": row.age,
                "city": row.city,
                "salary": float(row.salary),
                "salary_category": row.salary_category,
                "processed_at": str(row.processed_at)
            })

        return jsonify({
            "success": True,
            "page": page,
            "limit": limit,
            "count": len(data_list),
            "total_records": total_records,
            "total_pages": total_pages,
            "data": data_list
        })

    except Exception as e:

        print("Processed data error:", e)

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "Database error occurred while fetching processed data"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# API LOGS
# ============================================================

@app.route("/api/logs", methods=["GET"])
@require_api_key
def get_logs():
    """
    Get API Logs
    ---
    tags:
      - API Logs
    responses:
      200:
        description: API logs
      401:
        description: API key required
      403:
        description: Invalid API key
      500:
        description: Internal server error
    """

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                endpoint,
                method,
                status,
                message,
                created_at
            FROM ApiLogs
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        logs = []

        for row in rows:

            logs.append({
                "id": row.id,
                "endpoint": row.endpoint,
                "method": row.method,
                "status": row.status,
                "message": row.message,
                "created_at": str(row.created_at)
            })

        return jsonify({
            "success": True,
            "count": len(logs),
            "logs": logs
        })

    except Exception as e:

        print("Logs error:", e)

        return jsonify({
            "success": False,
            "error_code": 500,
            "error": "Internal Server Error",
            "message": "Unable to fetch logs"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
