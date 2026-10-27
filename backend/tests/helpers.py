"""Values shared by API tests. Kept out of conftest so imports do not re-run fixtures."""

TEST_USERNAME = "tester"
TEST_PASSWORD = "test-password-123"


def sample_expense(category_id: int, **overrides) -> dict:
    payload = {
        "amount": "12.50",
        "expense_date": "2024-06-15",
        "category_id": category_id,
        "description": "Lunch",
    }
    payload.update(overrides)
    return payload
