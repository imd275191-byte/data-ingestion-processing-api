import os
import pyodbc

DEFAULT_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=DESKTOP-CIRBMT0\\MRSQL2025;"
    "DATABASE=DataIngestionDB;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


def get_connection():
    connection_string = os.getenv(
        "DB_CONNECTION_STRING",
        DEFAULT_CONNECTION_STRING
    )
    return pyodbc.connect(connection_string, timeout=10)
