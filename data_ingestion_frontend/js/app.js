/* ============================================================
   DATAFLOW - FRONTEND APPLICATION
   Data Ingestion & Processing REST API
   ============================================================ */

const API_BASE_URL = "http://127.0.0.1:5000";
const API_KEY = "demo-api-key";

let processedCurrentPage = 1;
const processedPageSize = 10;

let lastCleanedDownloadUrl = "";
let lastCleanedFilename = "";


/* ============================================================
   COMMON HELPERS
   ============================================================ */

function getApiHeaders() {
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    };
}


function showResponse(elementId, message, type = "success") {
    const element = document.getElementById(elementId);

    if (!element) {
        return;
    }

    element.classList.remove("hidden");
    element.classList.remove("success", "error", "info");

    element.classList.add(type);

    element.textContent = message;
}


function formatNumber(value) {
    const number = Number(value);

    if (Number.isNaN(number)) {
        return "0";
    }

    return number.toLocaleString();
}


function formatDate(value) {
    if (!value) {
        return "-";
    }

    try {
        return new Date(value).toLocaleString();
    } catch {
        return value;
    }
}


/* ============================================================
   DASHBOARD
   ============================================================ */

async function loadSourceRecordsCount() {

    const element = document.getElementById("sourceRecordsCount");

    if (!element) {
        return;
    }

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/data?page=1&limit=1`,
            {
                method: "GET",
                headers: {
                    "X-API-Key": API_KEY
                }
            }
        );

        const result = await response.json();

        if (
            result.success &&
            result.data &&
            typeof result.total_records !== "undefined"
        ) {
            element.textContent =
                formatNumber(result.total_records);
        } else {
            element.textContent = "0";
        }

    } catch (error) {

        console.error(
            "Source records error:",
            error
        );

        element.textContent = "0";
    }
}


async function loadProcessedRecordsCount() {

    const element = document.getElementById(
        "processedRecordsCount"
    );

    if (!element) {
        return;
    }

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/processed-data?page=1&limit=1`,
            {
                method: "GET",
                headers: {
                    "X-API-Key": API_KEY
                }
            }
        );

        const result = await response.json();

        if (
            result.success &&
            result.data &&
            typeof result.total_records !== "undefined"
        ) {
            element.textContent =
                formatNumber(result.total_records);
        } else {
            element.textContent = "0";
        }

    } catch (error) {

        console.error(
            "Processed records error:",
            error
        );

        element.textContent = "0";
    }
}


/* ============================================================
   API HEALTH
   ============================================================ */

async function checkApiHealth() {

    const statusElement = document.getElementById(
        "apiStatusText"
    );

    const healthElement = document.getElementById(
        "healthResult"
    );

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/health`
        );

        const result = await response.json();

        if (result.success) {

            if (statusElement) {
                statusElement.textContent = "API Online";
            }

            if (healthElement) {

                healthElement.innerHTML = `
                    <strong>System Operational</strong>
                    <span>
                        API is running and database is
                        ${result.database || "connected"}.
                    </span>
                `;
            }

        } else {

            if (statusElement) {
                statusElement.textContent = "API Error";
            }

            if (healthElement) {
                healthElement.textContent =
                    "API health check failed.";
            }
        }

    } catch (error) {

        console.error(
            "Health check error:",
            error
        );

        if (statusElement) {
            statusElement.textContent = "API Offline";
        }

        if (healthElement) {
            healthElement.textContent =
                "Unable to connect to backend API.";
        }
    }
}


/* ============================================================
   SINGLE DATA INGESTION
   ============================================================ */

async function handleIngestion(event) {

    event.preventDefault();

    const button = document.getElementById(
        "ingestBtn"
    );

    const payload = {
        name: document.getElementById("name").value.trim(),
        email: document.getElementById("email").value.trim(),
        age: document.getElementById("age").value
            ? Number(document.getElementById("age").value)
            : null,
        city: document.getElementById("city").value.trim(),
        salary: document.getElementById("salary").value
            ? Number(document.getElementById("salary").value)
            : null
    };

    try {

        button.disabled = true;
        button.textContent = "Adding...";

        const response = await fetch(
            `${API_BASE_URL}/api/ingest`,
            {
                method: "POST",
                headers: getApiHeaders(),
                body: JSON.stringify(payload)
            }
        );

        const result = await response.json();

        if (response.ok && result.success) {

            showResponse(
                "ingestionResponse",
                result.message ||
                "Record added successfully.",
                "success"
            );

            document.getElementById(
                "ingestionForm"
            ).reset();

            await loadSourceRecordsCount();

        } else {

            showResponse(
                "ingestionResponse",
                result.message ||
                "Unable to add record.",
                "error"
            );
        }

    } catch (error) {

        console.error(
            "Ingestion error:",
            error
        );

        showResponse(
            "ingestionResponse",
            "Unable to connect to backend API.",
            "error"
        );

    } finally {

        button.disabled = false;
        button.textContent = "Add Record";
    }
}


/* ============================================================
   BATCH INGESTION
   ============================================================ */

function createBatchRecord(index) {

    const container = document.getElementById(
        "batchRecords"
    );

    if (!container) {
        return;
    }

    const record = document.createElement("div");

    record.className = "batch-record";

    record.innerHTML = `
        <div class="batch-record-top">

            <div class="record-number">
                <span>
                    ${String(index).padStart(2, "0")}
                </span>

                <strong>
                    Record ${index}
                </strong>
            </div>

            <button
                type="button"
                class="remove-batch-btn">
                Remove
            </button>

        </div>

        <div class="batch-fields">

            <div class="form-group">
                <label>Name</label>
                <input
                    type="text"
                    class="batch-name"
                    placeholder="Name">
            </div>

            <div class="form-group">
                <label>Email</label>
                <input
                    type="email"
                    class="batch-email"
                    placeholder="Email">
            </div>

            <div class="form-group">
                <label>Age</label>
                <input
                    type="number"
                    class="batch-age"
                    placeholder="Age">
            </div>

            <div class="form-group">
                <label>City</label>
                <input
                    type="text"
                    class="batch-city"
                    placeholder="City">
            </div>

            <div class="form-group">
                <label>Salary</label>
                <input
                    type="number"
                    class="batch-salary"
                    placeholder="Salary">
            </div>

        </div>
    `;

    const removeButton =
        record.querySelector(
            ".remove-batch-btn"
        );

    removeButton.addEventListener(
        "click",
        () => {

            record.remove();

            renumberBatchRecords();
        }
    );

    container.appendChild(record);
}


function renumberBatchRecords() {

    const records =
        document.querySelectorAll(
            "#batchRecords .batch-record"
        );

    records.forEach((record, index) => {

        const number =
            String(index + 1).padStart(2, "0");

        const numberElement =
            record.querySelector(
                ".record-number span"
            );

        const titleElement =
            record.querySelector(
                ".record-number strong"
            );

        if (numberElement) {
            numberElement.textContent =
                number;
        }

        if (titleElement) {
            titleElement.textContent =
                `Record ${index + 1}`;
        }
    });
}


async function handleBatchIngestion() {

    const records =
        document.querySelectorAll(
            "#batchRecords .batch-record"
        );

    const data = [];

    records.forEach(record => {

        data.push({

            name:
                record.querySelector(
                    ".batch-name"
                ).value.trim(),

            email:
                record.querySelector(
                    ".batch-email"
                ).value.trim(),

            age:
                record.querySelector(
                    ".batch-age"
                ).value
                    ? Number(
                        record.querySelector(
                            ".batch-age"
                        ).value
                    )
                    : null,

            city:
                record.querySelector(
                    ".batch-city"
                ).value.trim(),

            salary:
                record.querySelector(
                    ".batch-salary"
                ).value
                    ? Number(
                        record.querySelector(
                            ".batch-salary"
                        ).value
                    )
                    : null
        });
    });

    if (data.length === 0) {

        showResponse(
            "batchResponse",
            "Please add at least one record.",
            "error"
        );

        return;
    }

    const button =
        document.getElementById(
            "batchIngestBtn"
        );

    try {

        button.disabled = true;
        button.textContent = "Submitting...";

        const response = await fetch(
            `${API_BASE_URL}/api/batch-ingest`,
            {
                method: "POST",
                headers: getApiHeaders(),
                body: JSON.stringify({
                    data: data
                })
            }
        );

        const result = await response.json();

        if (response.ok && result.success) {

            showResponse(
                "batchResponse",
                result.message ||
                "Batch submitted successfully.",
                "success"
            );

            await loadSourceRecordsCount();

        } else {

            showResponse(
                "batchResponse",
                result.message ||
                "Batch ingestion failed.",
                "error"
            );
        }

    } catch (error) {

        console.error(
            "Batch ingestion error:",
            error
        );

        showResponse(
            "batchResponse",
            "Unable to connect to backend API.",
            "error"
        );

    } finally {

        button.disabled = false;
        button.textContent = "Submit Batch";
    }
}


/* ============================================================
   FILE SELECTION
   ============================================================ */

function handleCleanFileSelection() {

    const input =
        document.getElementById(
            "cleanFile"
        );

    const nameElement =
        document.getElementById(
            "selectedCleanFileName"
        );

    if (!input || !nameElement) {
        return;
    }

    if (input.files.length === 0) {

        nameElement.textContent =
            "No file selected";

        return;
    }

    const file =
        input.files[0];

    nameElement.textContent =
        `${file.name} (${formatFileSize(file.size)})`;
}


function formatFileSize(bytes) {

    if (bytes === 0) {
        return "0 Bytes";
    }

    const sizes = [
        "Bytes",
        "KB",
        "MB",
        "GB"
    ];

    const index =
        Math.floor(
            Math.log(bytes) /
            Math.log(1024)
        );

    return (
        Math.round(
            bytes /
            Math.pow(1024, index) *
            100
        ) / 100
    ) + " " + sizes[index];
}


window.handleCleanFileSelection = handleCleanFileSelection;


/* ============================================================
   FILE CLEANING
   ============================================================ */

async function cleanUploadedFile() {

    const input =
        document.getElementById(
            "cleanFile"
        );

    const button =
        document.getElementById(
            "cleanFileBtn"
        );

    if (!input || !button) {
        return;
    }

    if (!input.files || input.files.length === 0) {

        showResponse(
            "cleanFileResponse",
            "Please select a CSV, Excel, PDF or TXT file first.",
            "error"
        );

        return;
    }

    const file =
        input.files[0];

    const allowedExtensions = [
        ".csv",
        ".xlsx",
        ".xls",
        ".pdf",
        ".txt"
    ];

    const fileName =
        file.name.toLowerCase();

    const isAllowed =
        allowedExtensions.some(
            extension =>
                fileName.endsWith(extension)
        );

    if (!isAllowed) {

        showResponse(
            "cleanFileResponse",
            "Unsupported file format. Supported formats: CSV, Excel (.xlsx, .xls), PDF, TXT",
            "error"
        );

        return;
    }

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    try {

        button.disabled = true;
        button.textContent =
            "Cleaning File...";

        showResponse(
            "cleanFileResponse",
            "Uploading file and cleaning data. Please wait...",
            "info"
        );

        const response = await fetch(
            `${API_BASE_URL}/api/clean-file`,
            {
                method: "POST",

                headers: {
                    "X-API-Key": API_KEY
                },

                body: formData
            }
        );

        const result =
            await response.json();

        if (response.ok && result.success) {

            lastCleanedFilename =
                result.cleaned_filename || "";

            lastCleanedDownloadUrl =
                result.download_url || "";

            showResponse(
                "cleanFileResponse",
                result.message ||
                "File cleaned successfully.",
                "success"
            );

            displayCleaningReport(
    result
);

loadCleanedDataPreview(
    result.cleaned_filename
);

} else {

            showResponse(
                "cleanFileResponse",
                result.message ||
                "File cleaning failed.",
                "error"
            );

            hideCleaningReport();
        }

    } catch (error) {

        console.error(
            "File cleaning error:",
            error
        );

        showResponse(
            "cleanFileResponse",
            "Unable to connect to backend API.",
            "error"
        );

        hideCleaningReport();

    } finally {

        button.disabled = false;
        button.textContent =
            "Clean & Process File";
    }
}


window.cleanUploadedFile = cleanUploadedFile;
async function loadCleanedDataPreview(filename) {

    const tableBody = document.getElementById("cleanedPreviewTableBody");
    const countElement = document.getElementById("cleanedPreviewCount");

    if (!tableBody) {
        return;
    }

    tableBody.innerHTML = `
        <tr>
            <td colspan="6" class="empty-table">
                Loading cleaned data...
            </td>
        </tr>
    `;

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/download-cleaned/${encodeURIComponent(filename)}`,
            {
                method: "GET",
                headers: {
                    "X-API-Key": API_KEY
                }
            }
        );

        if (!response.ok) {
            throw new Error("Unable to load cleaned file.");
        }

        const csvText = await response.text();

        const rows = parseCSV(csvText);

        if (rows.length <= 1) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-table">
                        No cleaned records found.
                    </td>
                </tr>
            `;

            if (countElement) {
                countElement.textContent = "0 records";
            }

            return;
        }

        const headers = rows[0].map(function (header) {
            return header.trim().toLowerCase();
        });

        tableBody.innerHTML = "";

        rows.slice(1).forEach(function (row) {

            if (
                row.length === 0 ||
                row.every(function (value) {
                    return String(value).trim() === "";
                })
            ) {
                return;
            }

            const record = {};

            headers.forEach(function (header, index) {
                record[header] =
                    row[index] !== undefined
                        ? row[index].trim()
                        : "";
            });

            const tableRow = document.createElement("tr");

            tableRow.innerHTML = `
                <td>${escapeHtml(record.id || "-")}</td>
                <td>${escapeHtml(record.name || "Unknown")}</td>
                <td>${escapeHtml(record.email || "Unknown")}</td>
                <td>${escapeHtml(record.age || "-")}</td>
                <td>${escapeHtml(record.city || "Unknown")}</td>
                <td>${escapeHtml(record.salary || "-")}</td>
            `;

            tableBody.appendChild(tableRow);
        });

        const totalRows =
            tableBody.querySelectorAll("tr").length;

        if (countElement) {
            countElement.textContent =
                `${totalRows} records`;
        }

    } catch (error) {

        console.error(
            "Cleaned preview error:",
            error
        );

        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-table">
                    Unable to load cleaned data preview.
                </td>
            </tr>
        `;

        if (countElement) {
            countElement.textContent = "0 records";
        }
    }
}


function parseCSV(text) {

    const rows = [];
    let row = [];
    let value = "";
    let insideQuotes = false;

    for (let i = 0; i < text.length; i++) {

        const character = text[i];
        const nextCharacter = text[i + 1];

        if (character === '"') {

            if (insideQuotes && nextCharacter === '"') {
                value += '"';
                i++;
            } else {
                insideQuotes = !insideQuotes;
            }

        } else if (character === "," && !insideQuotes) {

            row.push(value);
            value = "";

        } else if (
            (character === "\n" || character === "\r") &&
            !insideQuotes
        ) {

            if (character === "\r" && nextCharacter === "\n") {
                i++;
            }

            row.push(value);
            rows.push(row);

            row = [];
            value = "";

        } else {

            value += character;
        }
    }

    if (value !== "" || row.length > 0) {
        row.push(value);
        rows.push(row);
    }

    return rows;
}


/* ============================================================
   CLEANING REPORT
   ============================================================ */

function displayCleaningReport(result) {

    const report =
        result.report || {};

    const reportElement =
        document.getElementById(
            "cleaningReport"
        );

    if (!reportElement) {
        return;
    }

    reportElement.classList.remove(
        "hidden"
    );

    document.getElementById(
        "cleanedFileType"
    ).textContent =
        result.file_type ||
        "File";

    document.getElementById(
        "originalRows"
    ).textContent =
        formatNumber(
            report.original_rows
        );

    document.getElementById(
        "finalRows"
    ).textContent =
        formatNumber(
            report.final_rows
        );

    document.getElementById(
        "rowsRemoved"
    ).textContent =
        formatNumber(
            report.rows_removed
        );

    document.getElementById(
        "duplicateRowsRemoved"
    ).textContent =
        formatNumber(
            report.duplicate_rows_removed
        );

    document.getElementById(
        "invalidEmailsFound"
    ).textContent =
        formatNumber(
            report.invalid_emails_found
        );

    document.getElementById(
        "missingValuesRemaining"
    ).textContent =
        formatNumber(
            report.missing_values_remaining
        );

    document.getElementById(
        "cleanedFileName"
    ).textContent =
        result.cleaned_filename ||
        "Cleaned file";
}


function hideCleaningReport() {

    const reportElement =
        document.getElementById(
            "cleaningReport"
        );

    if (reportElement) {

        reportElement.classList.add(
            "hidden"
        );
    }

    lastCleanedFilename = "";
    lastCleanedDownloadUrl = "";
}


/* ============================================================
   DOWNLOAD CLEANED FILE
   ============================================================ */

async function downloadCleanedFile() {

    if (!lastCleanedFilename) {

        showResponse(
            "cleanFileResponse",
            "Please clean a file first.",
            "error"
        );

        return;
    }

    const button =
        document.getElementById(
            "downloadCleanedBtn"
        );

    try {

        button.disabled = true;
        button.textContent =
            "Preparing Download...";

        const response = await fetch(
            `${API_BASE_URL}/api/download-cleaned/${encodeURIComponent(lastCleanedFilename)}`,
            {
                method: "GET",

                headers: {
                    "X-API-Key": API_KEY
                }
            }
        );

        if (!response.ok) {

            let message =
                "Unable to download cleaned file.";

            try {

                const errorResult =
                    await response.json();

                if (errorResult.message) {
                    message =
                        errorResult.message;
                }

            } catch {
                // Binary/error response
            }

            showResponse(
                "cleanFileResponse",
                message,
                "error"
            );

            return;
        }

        const blob =
            await response.blob();

        const blobUrl =
            window.URL.createObjectURL(
                blob
            );

        const link =
            document.createElement("a");

        link.href =
            blobUrl;

        link.download =
            lastCleanedFilename;

        document.body.appendChild(
            link
        );

        link.click();

        link.remove();

        window.URL.revokeObjectURL(
            blobUrl
        );

        showResponse(
            "cleanFileResponse",
            "Cleaned file downloaded successfully.",
            "success"
        );

    } catch (error) {

        console.error(
            "Download error:",
            error
        );

        showResponse(
            "cleanFileResponse",
            "Unable to download cleaned file.",
            "error"
        );

    } finally {

        button.disabled = false;
        button.textContent =
            "Download Cleaned File";
    }
}


/* ============================================================
   PROCESSED DATA
   ============================================================ */

async function loadProcessedData(
    page = processedCurrentPage
) {

    const tableBody =
        document.getElementById(
            "processedTableBody"
        );

    const pageInfo =
        document.getElementById(
            "processedPageInfo"
        );

    const countElement =
        document.getElementById(
            "processedDataCount"
        );

    if (!tableBody) {
        return;
    }

    processedCurrentPage = page;

    const searchElement =
        document.getElementById(
            "processedSearch"
        );

    const search =
        searchElement
            ? searchElement.value.trim()
            : "";

    
    const cityFilter =
        document.getElementById(
            "processedCityFilter"
        );

    const categoryFilter =
        document.getElementById(
            "processedCategoryFilter"
        );

    const city =
        cityFilter
            ? cityFilter.value.trim()
            : "";

    const salaryCategory =
        categoryFilter
            ? categoryFilter.value.trim()
            : "";
tableBody.innerHTML = `
        <tr>
            <td colspan="9" class="empty-table">
                Loading processed records...
            </td>
        </tr>
    `;

    try {

        let url =
            `${API_BASE_URL}/api/processed-data?page=${page}&limit=${processedPageSize}`;

        if (search) {

            url +=
                `&search=${encodeURIComponent(search)}`;
        }

        
        if (city) {

            url +=
                `&city=${encodeURIComponent(city)}`;
        }

        if (salaryCategory) {

            url +=
                `&salary_category=${encodeURIComponent(salaryCategory)}`;
        }
const response =
            await fetch(
                url,
                {
                    method: "GET",
                    headers: {
                        "X-API-Key": API_KEY
                    }
                }
            );

        const result =
            await response.json();

        if (
            !response.ok ||
            !result.success
        ) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-table">
                        ${
                            result.message ||
                            "Unable to load processed data."
                        }
                    </td>
                </tr>
            `;

            return;
        }

        /* FIX:
           Backend returns:
           result.data = [records]
           result.total_records = number
        */

        const records =
            Array.isArray(result.data)
                ? result.data
                : [];

        const totalRecords =
            typeof result.total_records !== "undefined"
                ? Number(result.total_records)
                : records.length;

        if (countElement) {

            countElement.textContent =
                `${formatNumber(totalRecords)} records`;
        }

        if (pageInfo) {

            const totalPages =
                Math.max(
                    1,
                    Number(result.total_pages) ||
                    Math.ceil(
                        totalRecords /
                        processedPageSize
                    )
                );

            pageInfo.textContent =
                `Page ${page} of ${totalPages}`;
        }

        if (records.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="empty-table">
                        No processed records found.
                    </td>
                </tr>
            `;

            updateProcessedPagination(
                totalRecords
            );

            return;
        }

        tableBody.innerHTML = "";

        records.forEach(record => {

            const row =
                document.createElement("tr");

            row.innerHTML = `
                <td>${record.id ?? "-"}</td>

                <td>${record.source_id ?? "-"}</td>

                <td>${escapeHtml(
                    record.name ?? "-"
                )}</td>

                <td>${escapeHtml(
                    record.email ?? "-"
                )}</td>

                <td>${record.age ?? "-"}</td>

                <td>${escapeHtml(
                    record.city ?? "-"
                )}</td>

                <td>${record.salary ?? "-"}</td>

                <td>${escapeHtml(
                    record.salary_category ?? "-"
                )}</td>

                <td>${formatDate(
                    record.processed_at
                )}</td>
            `;

            tableBody.appendChild(
                row
            );
        });

        updateProcessedPagination(
            totalRecords
        );

    } catch (error) {

        console.error(
            "Processed data error:",
            error
        );

        tableBody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-table">
                    Unable to connect to backend API.
                </td>
            </tr>
        `;
    }
}


function updateProcessedPagination(
    totalRecords
) {

    const previousButton =
        document.getElementById(
            "processedPrevBtn"
        );

    const nextButton =
        document.getElementById(
            "processedNextBtn"
        );

    const totalPages =
        Math.max(
            1,
            Math.ceil(
                totalRecords /
                processedPageSize
            )
        );

    if (previousButton) {

        previousButton.disabled =
            processedCurrentPage <= 1;
    }

    if (nextButton) {

        nextButton.disabled =
            processedCurrentPage >=
            totalPages;
    }
}


/* ============================================================
   API LOGS
   ============================================================ */

async function loadApiLogs() {

    const tableBody =
        document.getElementById(
            "logsTableBody"
        );

    if (!tableBody) {
        return;
    }

    tableBody.innerHTML = `
        <tr>
            <td colspan="6" class="empty-table">
                Loading API logs...
            </td>
        </tr>
    `;

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/logs?limit=50`,
                {
                    method: "GET",
                    headers: {
                        "X-API-Key": API_KEY
                    }
                }
            );

        const result =
            await response.json();

        if (
            !response.ok ||
            !result.success
        ) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-table">
                        ${
                            result.message ||
                            "Unable to load API logs."
                        }
                    </td>
                </tr>
            `;

            return;
        }

        const logs =
            Array.isArray(result.logs)
                ? result.logs
                : [];

        if (logs.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-table">
                        No API logs found.
                    </td>
                </tr>
            `;

            return;
        }

        tableBody.innerHTML = "";

        logs.forEach(log => {

            const row =
                document.createElement("tr");

            row.innerHTML = `
                <td>${log.id ?? "-"}</td>

                <td>${escapeHtml(
                    log.endpoint ?? "-"
                )}</td>

                <td>${escapeHtml(
                    log.method ?? "-"
                )}</td>

                <td>${escapeHtml(
                    log.status ?? "-"
                )}</td>

                <td>${escapeHtml(
                    log.message ?? "-"
                )}</td>

                <td>${formatDate(
                    log.created_at
                )}</td>
            `;

            tableBody.appendChild(
                row
            );
        });

    } catch (error) {

        console.error(
            "Logs error:",
            error
        );

        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-table">
                    Unable to connect to backend API.
                </td>
            </tr>
        `;
    }
}


/* ============================================================
   ETL PROCESSING
   ============================================================ */

async function runEtlProcessing() {

    const button =
        document.getElementById(
            "processEtlBtn"
        );

    try {

        button.disabled = true;
        button.innerHTML =
            "Processing... <span>â†’</span>";

        const response =
            await fetch(
                `${API_BASE_URL}/api/process`,
                {
                    method: "POST",
                    headers: {
                        "X-API-Key": API_KEY
                    }
                }
            );

        const result =
            await response.json();

        if (
            response.ok &&
            result.success
        ) {

            showResponse(
                "etlResult",
                result.message ||
                "ETL processing completed successfully.",
                "success"
            );

            const data =
                result.data || result;

            document.getElementById(
                "etlSourceRecords"
            ).textContent =
                formatNumber(
                    data.source_records
                );

            document.getElementById(
                "etlProcessedInserted"
            ).textContent =
                formatNumber(
                    data.processed_inserted
                );

            document.getElementById(
                "etlAlreadyProcessed"
            ).textContent =
                formatNumber(
                    data.already_processed
                );

            document.getElementById(
                "etlSummary"
            ).classList.remove(
                "hidden"
            );

            document.getElementById(
                "newProcessedCount"
            ).textContent =
                formatNumber(
                    data.processed_inserted
                );

            await loadProcessedRecordsCount();
            await loadProcessedData();

        } else {

            showResponse(
                "etlResult",
                result.message ||
                "ETL processing failed.",
                "error"
            );
        }

    } catch (error) {

        console.error(
            "ETL error:",
            error
        );

        showResponse(
            "etlResult",
            "Unable to connect to backend API.",
            "error"
        );

    } finally {

        button.disabled = false;

        button.innerHTML =
            "Run ETL Processing <span>â†’</span>";
    }
}


/* ============================================================
   HTML ESCAPE
   ============================================================ */

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* ============================================================
   NAVIGATION
   ============================================================ */

function setupNavigation() {

    const navLinks =
        document.querySelectorAll(
            ".nav-link"
        );

    navLinks.forEach(link => {

        link.addEventListener(
            "click",
            () => {

                navLinks.forEach(
                    item =>
                        item.classList.remove(
                            "active"
                        )
                );

                link.classList.add(
                    "active"
                );
            }
        );
    });


    const actionLinks =
        document.querySelectorAll(
            ".action-card"
        );

    actionLinks.forEach(link => {

        link.addEventListener(
            "click",
            () => {

                const target =
                    document.querySelector(
                        link.getAttribute(
                            "href"
                        )
                    );

                if (target) {

                    setTimeout(
                        () => {
                            target.scrollIntoView({
                                behavior: "smooth",
                                block: "start"
                            });
                        },
                        50
                    );
                }
            }
        );
    });
}


/* ============================================================
   MOBILE MENU
   ============================================================ */

function setupMobileMenu() {

    const menuButton =
        document.querySelector(
            ".mobile-menu"
        );

    const sidebar =
        document.querySelector(
            ".sidebar"
        );

    if (!menuButton || !sidebar) {
        return;
    }

    menuButton.addEventListener(
        "click",
        () => {

            sidebar.classList.toggle(
                "mobile-open"
            );
        }
    );
}


/* ============================================================
   REFRESH DASHBOARD
   ============================================================ */

async function refreshDashboard() {

    const button =
        document.getElementById(
            "refreshBtn"
        );

    if (button) {
        button.disabled = true;
    }

    await Promise.all([
        checkApiHealth(),
        loadSourceRecordsCount(),
        loadProcessedRecordsCount(),
        loadProcessedData(1),
        loadApiLogs()
    ]);

    const lastUpdated =
        document.getElementById(
            "lastUpdated"
        );

    if (lastUpdated) {

        lastUpdated.textContent =
            `Last updated: ${new Date().toLocaleString()}`;
    }

    if (button) {
        button.disabled = false;
    }
}


/* ============================================================
   EVENT LISTENERS
   ============================================================ */

function setupEventListeners() {

    /* Single ingestion */

    const ingestionForm =
        document.getElementById(
            "ingestionForm"
        );

    if (ingestionForm) {

        ingestionForm.addEventListener(
            "submit",
            handleIngestion
        );
    }


    /* Add batch record */

    const addBatchButton =
        document.getElementById(
            "addBatchBtn"
        );

    if (addBatchButton) {

        addBatchButton.addEventListener(
            "click",
            () => {

                const records =
                    document.querySelectorAll(
                        "#batchRecords .batch-record"
                    );

                createBatchRecord(
                    records.length + 1
                );
            }
        );
    }


    /* Batch submit */

    const batchButton =
        document.getElementById(
            "batchIngestBtn"
        );

    if (batchButton) {

        batchButton.addEventListener(
            "click",
            handleBatchIngestion
        );
    }


    /* File selection */

    const cleanFileInput =
        document.getElementById(
            "cleanFile"
        );

    if (cleanFileInput) {

        cleanFileInput.addEventListener(
            "change",
            handleCleanFileSelection
        );
    }


    /* Clean file */

    const cleanButton =
        document.getElementById(
            "cleanFileBtn"
        );

    if (cleanButton) {

        cleanButton.addEventListener(
            "click",
            cleanUploadedFile
        );
    }


    /* Download */

    const downloadButton =
        document.getElementById(
            "downloadCleanedBtn"
        );

    if (downloadButton) {

        downloadButton.addEventListener(
            "click",
            downloadCleanedFile
        );
    }


    /* ETL */

    const etlButton =
        document.getElementById(
            "processEtlBtn"
        );

    if (etlButton) {

        etlButton.addEventListener(
            "click",
            runEtlProcessing
        );
    }


    /* Refresh dashboard */

    const refreshButton =
        document.getElementById(
            "refreshBtn"
        );

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            refreshDashboard
        );
    }


    /* Processed data refresh */

    const processedRefresh =
        document.getElementById(
            "refreshProcessedBtn"
        );

    if (processedRefresh) {

        processedRefresh.addEventListener(
            "click",
            () => loadProcessedData(1)
        );
    }


    /* Processed previous */

    const processedPrevious =
        document.getElementById(
            "processedPrevBtn"
        );

    if (processedPrevious) {

        processedPrevious.addEventListener(
            "click",
            () => {

                if (
                    processedCurrentPage > 1
                ) {

                    loadProcessedData(
                        processedCurrentPage - 1
                    );
                }
            }
        );
    }


    /* Processed next */

    const processedNext =
        document.getElementById(
            "processedNextBtn"
        );

    if (processedNext) {

        processedNext.addEventListener(
            "click",
            () => {

                loadProcessedData(
                    processedCurrentPage + 1
                );
            }
        );
    }


    /* Apply processed data filter */

    const processedFilterButton =
        document.getElementById(
            "processedFilterBtn"
        );

    if (processedFilterButton) {

        processedFilterButton.addEventListener(
            "click",
            event => {

                event.preventDefault();

                loadProcessedData(1);
            }
        );
    }


    /* Search */

    const processedSearch =
        document.getElementById(
            "processedSearch"
        );

    if (processedSearch) {

        let searchTimer;

        processedSearch.addEventListener(
            "input",
            () => {

                clearTimeout(
                    searchTimer
                );

                searchTimer =
                    setTimeout(
                        () => {
                            loadProcessedData(1);
                        },
                        400
                    );
            }
        );
    }


    /* Logs */

    const logsRefresh =
        document.getElementById(
            "refreshLogsBtn"
        );

    if (logsRefresh) {

        logsRefresh.addEventListener(
            "click",
            loadApiLogs
        );
    }
}


/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        setupNavigation();

        setupMobileMenu();

        setupEventListeners();

        await refreshDashboard();
    }
);


/* NAVIGATION FIX ONLY
   Existing backend, database and other functions are untouched.
*/

document.addEventListener("DOMContentLoaded", function () {
    const navLinks = document.querySelectorAll(".nav-link");

    navLinks.forEach(function (link) {
        link.addEventListener("click", function (event) {
            event.preventDefault();

            const targetId = link.getAttribute("href");

            if (!targetId || !targetId.startsWith("#")) {
                return;
            }

            const target = document.querySelector(targetId);

            if (!target) {
                console.warn("Navigation target not found:", targetId);
                return;
            }

            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            navLinks.forEach(function (item) {
                item.classList.remove("active");
            });

            link.classList.add("active");
        });
    });
});

/* SOURCE DATA TABLE FIX ONLY
   Existing code, backend, database and other features are untouched.
*/

async function loadSourceRecords() {

    const tableBody =
        document.getElementById("sourceTableBody");

    const countElement =
        document.getElementById("sourceDataCount");

    const pageInfo =
        document.getElementById("sourcePageInfo");

    if (!tableBody) {
        return;
    }

    tableBody.innerHTML = `
        <tr>
            <td colspan="7" class="empty-table">
                Loading source records...
            </td>
        </tr>
    `;

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/api/data?page=1&limit=10`,
                {
                    method: "GET",
                    headers: {
                        "X-API-Key": API_KEY
                    }
                }
            );

        const result =
            await response.json();

        if (
            !response.ok ||
            !result.success
        ) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-table">
                        ${
                            result.message ||
                            "Unable to load source records."
                        }
                    </td>
                </tr>
            `;

            return;
        }

        const records =
            Array.isArray(result.data)
                ? result.data
                : [];

        const totalRecords =
            typeof result.total_records !== "undefined"
                ? Number(result.total_records)
                : records.length;

        if (countElement) {
            countElement.textContent =
                `${totalRecords} records`;
        }

        if (pageInfo) {
            pageInfo.textContent =
                totalRecords > 0
                    ? "Page 1 of 1"
                    : "Page 1";
        }

        if (records.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-table">
                        No source records found.
                    </td>
                </tr>
            `;

            return;
        }

        tableBody.innerHTML = "";

        records.forEach(function (record) {

            const row =
                document.createElement("tr");

            row.innerHTML = `
                <td>${record.id ?? "-"}</td>

                <td>${escapeHtml(
                    record.name ?? "-"
                )}</td>

                <td>${escapeHtml(
                    record.email ?? "-"
                )}</td>

                <td>${record.age ?? "-"}</td>

                <td>${escapeHtml(
                    record.city ?? "-"
                )}</td>

                <td>${record.salary ?? "-"}</td>

                <td>${formatDate(
                    record.created_at
                )}</td>
            `;

            tableBody.appendChild(row);
        });

    } catch (error) {

        console.error(
            "Source records load error:",
            error
        );

        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-table">
                    Unable to load source records.
                </td>
            </tr>
        `;
    }
}


document.addEventListener(
    "DOMContentLoaded",
    function () {

        const refreshButton =
            document.getElementById(
                "refreshSourceBtn"
            );

        if (refreshButton) {

            refreshButton.addEventListener(
                "click",
                function () {
                    loadSourceRecords();
                }
            );
        }

        loadSourceRecords();
    }
);


