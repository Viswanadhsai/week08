"""
KoalaTech Authenticated Ephemeral E2E Quality Gate
SIT722 - 10.3HD

This test validates a realistic KoalaTech business journey:

User authentication
        |
        v
Admin JWT
        |
        v
Student Service -> Course Service -> Enrollment Service

The test runs against an isolated Docker Compose environment and returns
a non-zero exit code if any business or security assertion fails.
"""

import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# =====================================================================
# 1. SERVICE LOCATIONS
# =====================================================================

USER_URL = os.getenv(
    "USER_SERVICE_URL",
    "http://localhost:18000",
)

STUDENT_URL = os.getenv(
    "STUDENT_SERVICE_URL",
    "http://localhost:18001",
)

COURSE_URL = os.getenv(
    "COURSE_SERVICE_URL",
    "http://localhost:18003",
)

ENROLLMENT_URL = os.getenv(
    "ENROLLMENT_SERVICE_URL",
    "http://localhost:18004",
)


# =====================================================================
# 2. TEMPORARY E2E ADMIN CREDENTIALS
# =====================================================================
# These match the disposable credentials created only inside
# docker-compose.e2e.yml.
# =====================================================================

ADMIN_USERNAME = os.getenv(
    "E2E_ADMIN_USERNAME",
    "e2e-admin",
)

ADMIN_PASSWORD = os.getenv(
    "E2E_ADMIN_PASSWORD",
    "E2EOnlyAdmin123!",
)


# =====================================================================
# 3. HTTP REQUEST HELPER
# =====================================================================
# Supports:
# - JSON request bodies
# - form-urlencoded authentication
# - Bearer token authentication
# =====================================================================

def request_json(
    method,
    url,
    payload=None,
    token=None,
    form_payload=None,
):
    headers = {
        "Accept": "application/json",
    }

    body = None

    # JSON body used by Student, Course and Enrollment APIs.
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    # OAuth2PasswordRequestForm expects form-urlencoded data.
    if form_payload is not None:
        headers["Content-Type"] = (
            "application/x-www-form-urlencoded"
        )

        body = urlencode(
            form_payload
        ).encode("utf-8")

    # Add the JWT only when accessing protected endpoints.
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url=url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=10,
        ) as response:

            content = response.read().decode(
                "utf-8"
            )

            if not content:
                return None

            return json.loads(content)

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8"
        )

        raise AssertionError(
            f"{method} {url} failed with HTTP "
            f"{error.code}: {error_body}"
        ) from error

    except URLError as error:
        raise AssertionError(
            f"Unable to reach {url}: "
            f"{error.reason}"
        ) from error


# =====================================================================
# 4. QUALITY-GATE ASSERTION HELPER
# =====================================================================

def check(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )

    print(
        f"[PASS] {message}"
    )


# =====================================================================
# 5. VERIFY ALL SERVICES ARE REACHABLE
# =====================================================================
# Docker validates internal health.
# Here we validate reachability from the E2E test runner.
# =====================================================================

def verify_service_health():
    print(
        "\n=== STEP 1: VERIFY SERVICE READINESS ==="
    )

    services = {
        "User Service":
            f"{USER_URL}/health",

        "Student Service":
            f"{STUDENT_URL}/health",

        "Course Service":
            f"{COURSE_URL}/health",

        "Enrollment Service":
            f"{ENROLLMENT_URL}/health",
    }

    for service_name, health_url in services.items():

        response = request_json(
            "GET",
            health_url,
        )

        check(
            response is not None,
            (
                f"{service_name} is healthy "
                "and externally reachable"
            ),
        )


# =====================================================================
# 6. AUTHENTICATE THROUGH THE REAL USER SERVICE
# =====================================================================
# We do not disable authentication for E2E testing.
#
# The test logs in through the production-style /auth/login endpoint,
# receives a real signed JWT and reuses it across protected services.
# =====================================================================

def authenticate_admin():
    print(
        "\n=== STEP 2: AUTHENTICATE E2E ADMIN ==="
    )

    login_response = request_json(
        "POST",
        f"{USER_URL}/auth/login",
        form_payload={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        },
    )

    access_token = login_response.get(
        "access_token"
    )

    check(
        bool(access_token),
        "User Service issued a JWT access token",
    )

    check(
        login_response.get(
            "token_type"
        ) == "bearer",
        "Authentication response returned bearer token type",
    )

    # Verify the token against User Service itself.
    current_user = request_json(
        "GET",
        f"{USER_URL}/auth/me",
        token=access_token,
    )

    check(
        current_user["username"]
        == ADMIN_USERNAME,
        "JWT identifies the temporary E2E administrator",
    )

    check(
        current_user["role"]
        == "admin",
        "Authenticated E2E user has admin role",
    )

    return access_token


# =====================================================================
# 7. CREATE AND VERIFY STUDENT
# =====================================================================

def create_and_verify_student(
    run_id,
    token,
):
    print(
        "\n=== STEP 3: CREATE AND VERIFY STUDENT ==="
    )

    student_id = (
        f"S10HD{run_id}"
    )

    payload = {
        "student_id":
            student_id,

        "first_name":
            "Ephemeral",

        "last_name":
            "Student",

        "email":
            (
                f"e2e.{run_id.lower()}"
                "@koalatech.edu.au"
            ),

        "phone":
            "0400000001",

        "date_of_birth":
            "2000-05-15",

        "program":
            "Master of Information Technology",

        "year_level":
            2,
    }

    created = request_json(
        "POST",
        f"{STUDENT_URL}/students",
        payload=payload,
        token=token,
    )

    check(
        created["student_id"]
        == student_id,
        "Student API returned the generated student ID",
    )

    check(
        created["email"]
        == payload["email"],
        "Student email was persisted correctly",
    )

    retrieved = request_json(
        "GET",
        (
            f"{STUDENT_URL}/students/"
            f"{student_id}"
        ),
        token=token,
    )

    check(
        retrieved["student_id"]
        == student_id,
        "Student was retrieved from temporary PostgreSQL",
    )

    check(
        retrieved["program"]
        == "Master of Information Technology",
        "Retrieved student contains expected program",
    )

    return retrieved


# =====================================================================
# 8. CREATE AND VERIFY COURSE
# =====================================================================

def create_and_verify_course(
    run_id,
    token,
):
    print(
        "\n=== STEP 4: CREATE AND VERIFY COURSE ==="
    )

    course_id = (
        f"C10HD{run_id}"
    )

    payload = {
        "course_id":
            course_id,

        "course_code":
            f"HD{run_id[:5]}",

        "course_name":
            "Ephemeral DevOps Quality Engineering",

        "description":
            (
                "Temporary course created by the "
                "KoalaTech 10.3HD E2E quality gate."
            ),

        "credit_points":
            12,

        "semester":
            "Trimester 2",

        "academic_year":
            2026,
    }

    created = request_json(
        "POST",
        f"{COURSE_URL}/courses",
        payload=payload,
        token=token,
    )

    check(
        created["course_id"]
        == course_id,
        "Course API returned the generated course ID",
    )

    check(
        created["course_name"]
        == payload["course_name"],
        "Course name was persisted correctly",
    )

    retrieved = request_json(
        "GET",
        (
            f"{COURSE_URL}/courses/"
            f"{course_id}"
        ),
        token=token,
    )

    check(
        retrieved["course_id"]
        == course_id,
        "Course was retrieved from temporary PostgreSQL",
    )

    return retrieved


# =====================================================================
# 9. CREATE CROSS-SERVICE ENROLLMENT
# =====================================================================

def create_enrollment(
    student,
    course,
    token,
):
    print(
        "\n=== STEP 5: CREATE ENROLLMENT RELATIONSHIP ==="
    )

    payload = {
        "student_id":
            student["student_id"],

        "course_id":
            course["course_id"],
    }

    created = request_json(
        "POST",
        f"{ENROLLMENT_URL}/enrollments",
        payload=payload,
        token=token,
    )

    check(
        created["student_id"]
        == student["student_id"],
        (
            "Enrollment references student "
            "created by Student Service"
        ),
    )

    check(
        created["course_id"]
        == course["course_id"],
        (
            "Enrollment references course "
            "created by Course Service"
        ),
    )

    check(
        created.get(
            "enrollment_id"
        ) is not None,
        "Enrollment Service generated enrollment ID",
    )

    return created


# =====================================================================
# 10. VERIFY BUSINESS RELATIONSHIP
# =====================================================================

def verify_enrollment(
    student,
    course,
    enrollment,
    token,
):
    print(
        "\n=== STEP 6: VERIFY COMPLETE BUSINESS JOURNEY ==="
    )

    enrollment_id = (
        enrollment["enrollment_id"]
    )

    # ---------------------------------------------------------------
    # Direct enrollment lookup
    # ---------------------------------------------------------------

    direct = request_json(
        "GET",
        (
            f"{ENROLLMENT_URL}/enrollments/"
            f"{enrollment_id}"
        ),
        token=token,
    )

    check(
        direct["student_id"]
        == student["student_id"]
        and direct["course_id"]
        == course["course_id"],
        (
            "Direct enrollment lookup preserved "
            "student-course relationship"
        ),
    )

    # ---------------------------------------------------------------
    # Verify from student direction
    # ---------------------------------------------------------------

    student_results = request_json(
        "GET",
        (
            f"{ENROLLMENT_URL}/enrollments/student/"
            f"{student['student_id']}"
        ),
        token=token,
    )

    student_match = any(
        item["course_id"]
        == course["course_id"]
        for item in student_results
    )

    check(
        student_match,
        (
            "Student lookup contains expected "
            "course enrollment"
        ),
    )

    # ---------------------------------------------------------------
    # Verify from course direction
    # ---------------------------------------------------------------

    course_results = request_json(
        "GET",
        (
            f"{ENROLLMENT_URL}/enrollments/course/"
            f"{course['course_id']}"
        ),
        token=token,
    )

    course_match = any(
        item["student_id"]
        == student["student_id"]
        for item in course_results
    )

    check(
        course_match,
        (
            "Course lookup contains expected "
            "student enrollment"
        ),
    )

    check(
        direct["status"]
        == enrollment["status"],
        "Enrollment status remained consistent",
    )


# =====================================================================
# 11. CONTROLLED QUALITY-GATE FAILURE
# =====================================================================
# GitHub Actions will later expose this as a workflow input.
#
# false -> normal production-style validation
# true  -> controlled demonstration that E2E failure blocks CI
# =====================================================================

def controlled_failure_demo():
    force_failure = (
        os.getenv(
            "E2E_FORCE_FAILURE",
            "false",
        ).lower()
        == "true"
    )

    if force_failure:

        print(
            "\n=== CONTROLLED FAILURE DEMONSTRATION ==="
        )

        check(
            False,
            (
                "Controlled E2E assertion blocked "
                "the pipeline successfully"
            ),
        )


# =====================================================================
# 12. EXECUTE THE COMPLETE AUTHENTICATED JOURNEY
# =====================================================================

def main():
    print(
        "=" * 72
    )

    print(
        "KOALATECH 10.3HD - AUTHENTICATED EPHEMERAL E2E QUALITY GATE"
    )

    print(
        "=" * 72
    )

    # Unique data every execution means repeated pipeline runs do not
    # depend on records created by previous executions.
    run_id = (
        uuid.uuid4()
        .hex[:8]
        .upper()
    )

    print(
        f"Unique E2E run ID: {run_id}"
    )

    verify_service_health()

    token = authenticate_admin()

    student = create_and_verify_student(
        run_id,
        token,
    )

    course = create_and_verify_course(
        run_id,
        token,
    )

    enrollment = create_enrollment(
        student,
        course,
        token,
    )

    verify_enrollment(
        student,
        course,
        enrollment,
        token,
    )

    controlled_failure_demo()

    print(
        "\n" + "=" * 72
    )

    print(
        "QUALITY GATE: PASS"
    )

    print(
        "Authentication -> Student -> Course -> Enrollment "
        "journey validated successfully."
    )

    print(
        "=" * 72
    )


# =====================================================================
# 13. CI-FRIENDLY EXIT CODE
# =====================================================================
#
# exit 0 -> E2E quality gate passed
# exit 1 -> E2E quality gate failed
#
# GitHub Actions can therefore use this test as a real deployment gate.
# =====================================================================

if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print(
            "\n" + "=" * 72
        )

        print(
            "QUALITY GATE: FAIL"
        )

        print(
            f"Reason: {error}"
        )

        print(
            "=" * 72
        )

        sys.exit(1)