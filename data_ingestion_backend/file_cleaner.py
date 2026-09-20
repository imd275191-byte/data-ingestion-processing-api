
import os
import re
import pandas as pd
import pdfplumber


# ============================================================
# FILE CLEANER
# Supports:
# CSV
# Excel (.xlsx)
# Excel (.xls)
# PDF
# TXT
# ============================================================


def normalize_column_name(column_name):
    """
    Convert column names into a clean and consistent format.

    Example:
        " First Name " -> "first_name"
        "Email Address" -> "email_address"
    """

    column_name = str(column_name).strip().lower()

    column_name = re.sub(r"\s+", "_", column_name)

    column_name = re.sub(r"[^a-z0-9_]", "", column_name)

    column_name = re.sub(r"_+", "_", column_name)

    return column_name.strip("_")


def clean_column_names(df):
    """
    Clean all column names.
    """

    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    return df


def normalize_missing_values(df):
    """
    Convert common empty/missing values into pandas NA.
    """

    missing_values = [
        "",
        " ",
        "na",
        "n/a",
        "NA",
        "N/A",
        "null",
        "NULL",
        "none",
        "None",
        "-",
        "--"
    ]

    df = df.replace(
        missing_values,
        pd.NA
    )

    return df


def trim_text_values(df):
    """
    Remove unnecessary spaces from text columns.
    """

    for column in df.select_dtypes(
        include=["object"]
    ).columns:

        df[column] = df[column].apply(
            lambda value: value.strip()
            if isinstance(value, str)
            else value
        )

    return df


def normalize_email_columns(df):
    """
    Normalize email columns.

    Only:
        - remove spaces
        - convert email to lowercase

    IMPORTANT:
        This function does NOT create or replace
        missing/invalid emails.
    """

    for column in df.columns:

        if "email" in column.lower():

            df[column] = df[column].apply(
                lambda value: value.lower().strip()
                if isinstance(value, str)
                else value
            )

    return df


def convert_numeric_columns(df):
    """
    Try to convert columns that appear to contain numeric data.

    Invalid numeric values become missing values.
    """

    for column in df.columns:

        if df[column].dtype == "object":

            converted = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            non_empty_count = (
                df[column].notna().sum()
            )

            if non_empty_count > 0:

                numeric_count = (
                    converted.notna().sum()
                )

                numeric_ratio = (
                    numeric_count /
                    non_empty_count
                )

                if numeric_ratio >= 0.70:

                    df[column] = converted

    return df


def validate_email_values(df):
    """
    Detect invalid email values.

    Invalid emails are converted to missing values.

    IMPORTANT:
        Invalid emails are NOT replaced with
        another person's email.
    """

    invalid_count = 0

    email_pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    for column in df.columns:

        if "email" not in column.lower():
            continue

        for index in df.index:

            value = df.at[
                index,
                column
            ]

            if pd.isna(value):
                continue

            value = str(value).strip()

            if not re.match(
                email_pattern,
                value
            ):

                df.at[
                    index,
                    column
                ] = pd.NA

                invalid_count += 1

    return df, invalid_count


def fill_missing_values(df):
    """
    Fill missing values using safe rules.

    IMPORTANT EMAIL RULE:
        Email columns are NEVER filled with
        the most common email address.

        Missing/invalid emails become:
            Unknown

    Numeric columns:
        Median value

    Name column:
        Unknown

    Other text columns:
        Most common value

    If no mode exists:
        Unknown
    """

    for column in df.columns:

        if df[column].isna().sum() == 0:
            continue

        # ====================================================
        # EMAIL COLUMN
        # ====================================================

        if "email" in column.lower():

            df[column] = (
                df[column].fillna(
                    "Unknown"
                )
            )

            continue

        # ====================================================
        # NUMERIC COLUMN
        # ====================================================

        if pd.api.types.is_numeric_dtype(
            df[column]
        ):

            if df[column].notna().sum() > 0:

                median_value = (
                    df[column].median()
                )

                df[column] = (
                    df[column].fillna(
                        median_value
                    )
                )

            else:

                df[column] = (
                    df[column].fillna(
                        0
                    )
                )

            continue

        # ====================================================
        # NAME COLUMN
        # ====================================================

        if column.lower() == "name":

            df[column] = (
                df[column].fillna(
                    "Unknown"
                )
            )

            continue

        # ====================================================
        # TEXT / OTHER COLUMN
        # ====================================================

        mode_values = (
            df[column].mode(
                dropna=True
            )
        )

        if len(mode_values) > 0:

            mode_value = (
                mode_values.iloc[0]
            )

            df[column] = (
                df[column].fillna(
                    mode_value
                )
            )

        else:

            df[column] = (
                df[column].fillna(
                    "Unknown"
                )
            )

    return df

def remove_empty_rows(df):
    """
    Remove rows where every value is empty.
    """

    before = len(df)

    df = df.dropna(
        how="all"
    )

    removed = (
        before -
        len(df)
    )

    return df, removed


def remove_duplicate_rows(df):
    """
    Remove duplicate records while ignoring the ID column.

    The ID column is not used for duplicate detection because
    the same record can have different IDs.
    """

    before = len(df)

    # ========================================================
    # DUPLICATE CHECK
    # ========================================================

    duplicate_columns = [
        column
        for column in df.columns
        if column.lower() != "id"
    ]

    if len(duplicate_columns) > 0:

        df = df.drop_duplicates(
            subset=duplicate_columns,
            keep="first"
        )

    else:

        df = df.drop_duplicates(
            keep="first"
        )

    removed = (
        before -
        len(df)
    )

    return df, removed

def remove_invalid_age_salary_rows(df):
    """
    Remove rows with invalid age or negative salary.

    Valid age:
        0 to 120

    Valid salary:
        0 or greater
    """

    before = len(df)

    # ========================================================
    # AGE VALIDATION
    # ========================================================

    if "age" in df.columns:

        age_values = pd.to_numeric(
            df["age"],
            errors="coerce"
        )

        invalid_age = (
            age_values.notna()
            &
            (
                (age_values < 0)
                |
                (age_values > 120)
            )
        )

        df = df.loc[
            ~invalid_age
        ].copy()

    # ========================================================
    # SALARY VALIDATION
    # ========================================================

    if "salary" in df.columns:

        salary_values = pd.to_numeric(
            df["salary"],
            errors="coerce"
        )

        invalid_salary = (
            salary_values.notna()
            &
            (salary_values < 0)
        )

        df = df.loc[
            ~invalid_salary
        ].copy()

    removed = (
        before -
        len(df)
    )

    return df, removed


def normalize_city_values(df):
    """
    Normalize city names to proper title case.
    """

    if "city" in df.columns:

        df["city"] = (
            df["city"]
            .astype("string")
            .str.strip()
            .str.title()
        )

    return df
# ============================================================
# PDF HELPERS
# ============================================================


def clean_pdf_cell(value):
    """
    Clean one PDF cell value.
    """

    if value is None:
        return None

    value = str(value)

    value = value.replace(
        "\n",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    value = value.strip()

    if value == "":
        return None

    return value


def build_dataframe_from_pdf_table(table):
    """
    Convert one pdfplumber table into a pandas DataFrame.
    """

    if not table:
        return None

    cleaned_rows = []

    for row in table:

        if not row:
            continue

        cleaned_row = [
            clean_pdf_cell(value)
            for value in row
        ]

        if all(
            value is None
            for value in cleaned_row
        ):
            continue

        cleaned_rows.append(
            cleaned_row
        )

    if len(cleaned_rows) < 2:
        return None

    header = cleaned_rows[0]

    column_count = len(header)

    cleaned_header = []

    for index, value in enumerate(
        header
    ):

        if value is None:

            cleaned_header.append(
                f"column_{index + 1}"
            )

        else:

            cleaned_header.append(
                value
            )

    data_rows = []

    for row in cleaned_rows[1:]:

        row = list(row)

        if len(row) < column_count:

            row += (
                [None] *
                (
                    column_count -
                    len(row)
                )
            )

        if len(row) > column_count:

            row = row[
                :column_count
            ]

        data_rows.append(
            row
        )

    if not data_rows:
        return None

    return pd.DataFrame(
        data_rows,
        columns=cleaned_header
    )


def parse_pipe_separated_pdf_text(lines):
    """
    Parse PDF text where columns are separated by '|'.
    """

    pipe_lines = []

    for line in lines:

        if not line:
            continue

        line = str(line).strip()

        if "|" not in line:
            continue

        parts = [
            part.strip()
            for part in line.split("|")
        ]

        if len(parts) >= 2:

            pipe_lines.append(
                parts
            )

    if len(pipe_lines) < 2:
        return None

    header = pipe_lines[0]

    column_count = max(
        len(row)
        for row in pipe_lines
    )

    if len(header) < column_count:

        header += (
            [None] *
            (
                column_count -
                len(header)
            )
        )

    if len(header) > column_count:

        header = header[
            :column_count
        ]

    cleaned_header = []

    for index, value in enumerate(
        header
    ):

        if (
            value is None
            or str(value).strip() == ""
        ):

            cleaned_header.append(
                f"column_{index + 1}"
            )

        else:

            cleaned_header.append(
                str(value).strip()
            )

    data_rows = []

    for row in pipe_lines[1:]:

        row = list(row)

        if len(row) < column_count:

            row += (
                [None] *
                (
                    column_count -
                    len(row)
                )
            )

        if len(row) > column_count:

            row = row[
                :column_count
            ]

        data_rows.append(
            row
        )

    if not data_rows:
        return None

    return pd.DataFrame(
        data_rows,
        columns=cleaned_header
    )


def extract_pdf_tables(file_path):
    """
    Extract structured data from a PDF.

    Extraction priority:

    1. Real PDF tables using pdfplumber
    2. Pipe-separated text tables
    3. Normal PDF text as one-column data
    """

    all_tables = []

    all_text = []

    # ========================================================
    # READ PDF
    # ========================================================

    with pdfplumber.open(
        file_path
    ) as pdf:

        for page in pdf.pages:

            # ------------------------------------------------
            # Try actual PDF table extraction
            # ------------------------------------------------

            tables = (
                page.extract_tables()
            )

            if tables:

                for table in tables:

                    if table:

                        all_tables.append(
                            table
                        )

            # ------------------------------------------------
            # Always extract text as fallback
            # ------------------------------------------------

            text = (
                page.extract_text()
            )

            if text:

                all_text.extend(
                    text.splitlines()
                )

    # ========================================================
    # METHOD 1
    # REAL PDF TABLE
    # ========================================================

    if all_tables:

        dataframes = []

        for table in all_tables:

            dataframe = (
                build_dataframe_from_pdf_table(
                    table
                )
            )

            if dataframe is not None:

                dataframes.append(
                    dataframe
                )

        if dataframes:

            if len(dataframes) == 1:

                return dataframes[0]

            first_columns = list(
                dataframes[0].columns
            )

            same_structure = all(
                list(dataframe.columns)
                == first_columns
                for dataframe in dataframes
            )

            if same_structure:

                return pd.concat(
                    dataframes,
                    ignore_index=True
                )

            return dataframes[0]

    # ========================================================
    # METHOD 2
    # PIPE-SEPARATED PDF TEXT
    # ========================================================

    pipe_dataframe = (
        parse_pipe_separated_pdf_text(
            all_text
        )
    )

    if pipe_dataframe is not None:

        return pipe_dataframe

    # ========================================================
    # METHOD 3
    # NORMAL PDF TEXT
    # ========================================================

    cleaned_text = []

    for line in all_text:

        line = str(line).strip()

        if line:

            cleaned_text.append(
                line
            )

    if cleaned_text:

        return pd.DataFrame(
            {
                "text": cleaned_text
            }
        )

    # ========================================================
    # NOTHING FOUND
    # ========================================================

    raise ValueError(
        "No readable text or table "
        "was found in the PDF."
    )


# ============================================================
# TXT HELPERS
# ============================================================


def read_text_file(file_path):
    """
    Read a TXT file and automatically detect
    a common column separator.

    Supported structured TXT separators:

        |
        ,
        ;
        Tab

    If no structured separator is detected,
    the TXT file is treated as one-column text data.
    """

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1"
    ]

    content = None

    for encoding in encodings:

        try:

            with open(
                file_path,
                "r",
                encoding=encoding
            ) as file:

                content = file.read()

            break

        except UnicodeDecodeError:

            continue

    if content is None:

        raise ValueError(
            "TXT file could not be read "
            "using supported text encodings."
        )

    content = content.lstrip(
        "\ufeff"
    )

    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    if not lines:

        raise ValueError(
            "TXT file is empty."
        )

    separators = [
        "|",
        "\t",
        ";",
        ","
    ]

    best_separator = None
    best_score = 0

    for separator in separators:

        counts = []

        for line in lines:

            counts.append(
                line.count(separator)
            )

        if not counts:
            continue

        positive_counts = [
            count
            for count in counts
            if count > 0
        ]

        if len(positive_counts) < 2:
            continue

        frequency = len(
            positive_counts
        )

        average_count = (
            sum(positive_counts) /
            len(positive_counts)
        )

        score = (
            frequency *
            average_count
        )

        if score > best_score:

            best_score = score

            best_separator = (
                separator
            )

    if best_separator is not None:

        try:

            rows = []

            for line in lines:

                row = [
                    part.strip()
                    for part in line.split(
                        best_separator
                    )
                ]

                rows.append(row)

            if len(rows) >= 2:

                column_count = max(
                    len(row)
                    for row in rows
                )

                header = list(
                    rows[0]
                )

                if len(header) < column_count:

                    header += (
                        [None] *
                        (
                            column_count -
                            len(header)
                        )
                    )

                if len(header) > column_count:

                    header = header[
                        :column_count
                    ]

                cleaned_header = []

                for index, value in enumerate(
                    header
                ):

                    if (
                        value is None
                        or str(value).strip() == ""
                    ):

                        cleaned_header.append(
                            f"column_{index + 1}"
                        )

                    else:

                        cleaned_header.append(
                            str(value).strip()
                        )

                data_rows = []

                for row in rows[1:]:

                    row = list(row)

                    if len(row) < column_count:

                        row += (
                            [None] *
                            (
                                column_count -
                                len(row)
                            )
                        )

                    if len(row) > column_count:

                        row = row[
                            :column_count
                        ]

                    data_rows.append(
                        row
                    )

                if data_rows:

                    return pd.DataFrame(
                        data_rows,
                        columns=cleaned_header
                    )

        except Exception:

            pass

    return pd.DataFrame(
        {
            "text": lines
        }
    )


# ============================================================
# INPUT FILE READER
# ============================================================


def read_input_file(file_path):
    """
    Read CSV, Excel, PDF or TXT file.
    """

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".csv":

        df = pd.read_csv(
            file_path
        )

        file_type = "CSV"

    elif extension == ".xlsx":

        df = pd.read_excel(
            file_path,
            engine="openpyxl"
        )

        file_type = "Excel"

    elif extension == ".xls":

        df = pd.read_excel(
            file_path,
            engine="xlrd"
        )

        file_type = "Excel"

    elif extension == ".pdf":

        df = extract_pdf_tables(
            file_path
        )

        file_type = "PDF"

    elif extension == ".txt":

        df = read_text_file(
            file_path
        )

        file_type = "TXT"

    else:

        raise ValueError(
            "Unsupported file type. "
            "Supported files are "
            "CSV, XLSX, XLS, PDF and TXT."
        )

    return df, file_type


# ============================================================
# DATAFRAME CLEANING PIPELINE
# ============================================================



def clean_dataframe(df):
    """
    Complete data cleaning pipeline.
    """

    original_rows = len(df)

    original_columns = len(
        df.columns
    )

    # ========================================================
    # STEP 1
    # Column names
    # ========================================================

    df = clean_column_names(
        df
    )

    # ========================================================
    # STEP 2
    # Missing values
    # ========================================================

    df = normalize_missing_values(
        df
    )

    # ========================================================
    # STEP 3
    # Remove completely empty rows
    # ========================================================

    df, empty_rows_removed = (
        remove_empty_rows(
            df
        )
    )

    # ========================================================
    # STEP 4
    # Trim text
    # ========================================================

    df = trim_text_values(
        df
    )
    # ========================================================
    # Normalize city
    # ========================================================

    df = normalize_city_values(
        df
    )
    # ========================================================
    # STEP 5
    # Normalize email
    # ========================================================

    df = normalize_email_columns(
        df
    )

    # ========================================================
    # STEP 6
    # Convert numeric columns
    # ========================================================

    df = convert_numeric_columns(
        df
    )

    # ========================================================
    # STEP 7
    # Validate email
    # ========================================================

    df, invalid_emails = (
        validate_email_values(
            df
        )
    )

    # ========================================================
    # STEP 8
    # Remove duplicates
    # ========================================================

    df, duplicate_rows_removed = (
        remove_duplicate_rows(
            df
        )
    )

    # ========================================================
    # STEP 9
    # Remove invalid age and salary rows
    # ========================================================

    df, invalid_age_salary_rows_removed = (
        remove_invalid_age_salary_rows(
            df
        )
    )


    # ========================================================
    # STEP 10
    # Fill missing values
    # ========================================================

    df = fill_missing_values(
        df
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    final_rows = len(df)

    final_columns = len(
        df.columns
    )

    report = {

        "original_rows":
            original_rows,

        "final_rows":
            final_rows,

        "rows_removed":
            original_rows -
            final_rows,

        "original_columns":
            original_columns,

        "final_columns":
            final_columns,

        "empty_rows_removed":
            empty_rows_removed,

        "duplicate_rows_removed":
            duplicate_rows_removed,

        "invalid_emails_found":
            invalid_emails,
        "invalid_age_salary_rows_removed":
            invalid_age_salary_rows_removed,

        "missing_values_remaining":
            int(
                df.isna().sum().sum()
            )
    }

    return df, report


# ============================================================
# COMPLETE FILE CLEANING
# ============================================================


def clean_file(
    file_path,
    output_directory
):
    """
    Read and clean a CSV, Excel, PDF or TXT file.

    Returns:
        file type
        output filename
        output path
        cleaning report
    """

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    # ========================================================
    # READ INPUT
    # ========================================================

    df, file_type = (
        read_input_file(
            file_path
        )
    )

    # ========================================================
    # CLEAN DATA
    # ========================================================

    cleaned_df, report = (
        clean_dataframe(
            df
        )
    )

    # ========================================================
    # CREATE OUTPUT FILE NAME
    # ========================================================

    original_name = os.path.splitext(
        os.path.basename(
            file_path
        )
    )[0]

    safe_name = normalize_column_name(
        original_name
    )

    output_filename = (
        f"{safe_name}_cleaned.xlsx"
    )

    output_path = os.path.join(
        output_directory,
        output_filename
    )

    # ========================================================
    # SAVE FRESH CLEANED EXCEL
    # ========================================================

    cleaned_df.to_excel(
        output_path,
        index=False
    )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "file_type":
            file_type,

        "output_file":
            output_filename,

        "output_path":
            output_path,

        "report":
            report
    }


# ============================================================
# SIMPLE DIRECT TEST
# ============================================================


if __name__ == "__main__":

    print("=" * 60)

    print(
        "FILE CLEANER MODULE"
    )

    print("=" * 60)

    print(
        "Supported formats:"
    )

    print(
        "1. CSV"
    )

    print(
        "2. Excel (.xlsx)"
    )

    print(
        "3. Excel (.xls)"
    )

    print(
        "4. PDF"
    )

    print(
        "5. TXT"
    )

    print("=" * 60)

    print(
        "TXT structured separators:"
    )

    print(
        "Pipe (|)"
    )

    print(
        "Comma (,)"
    )

    print(
        "Semicolon (;)"
    )

    print(
        "Tab"
    )

    print("=" * 60)

    print(
        "PDF table extraction:"
    )

    print(
        "Real PDF tables supported"
    )

    print(
        "Pipe-separated PDF tables supported"
    )

    print("=" * 60)

    print(
        "File cleaner module loaded successfully."
    )
