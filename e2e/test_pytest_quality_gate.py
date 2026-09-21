"""
Pytest entry point for the KoalaTech 10.3HD E2E quality gate.

The detailed business logic remains in test_koalatech_journey.py.
Pytest is responsible for executing that complete authenticated journey
and converting any failed assertion into a failed CI quality gate.
"""

from e2e.test_koalatech_journey import main


def test_authenticated_koalatech_business_journey():
    """
    Validate the complete ephemeral KoalaTech journey:

    Authentication
        -> Student
        -> Course
        -> Enrollment
        -> Cross-service verification
    """

    main()