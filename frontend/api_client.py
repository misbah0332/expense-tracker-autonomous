"""HTTP client for the expense tracker API. The UI never opens a database connection."""

from datetime import date

import httpx


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ExpenseApi:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def login(self, username: str, password: str) -> str:
        body = self._request("POST", "/api/auth/login", json={"username": username, "password": password})
        self.token = body["access_token"]
        return self.token

    def logout(self) -> None:
        self._request("POST", "/api/auth/logout")
        self.token = None

    def me(self) -> dict:
        return self._request("GET", "/api/auth/me")

    def list_categories(self) -> list[dict]:
        return self._request("GET", "/api/categories")

    def create_category(self, name: str) -> dict:
        return self._request("POST", "/api/categories", json={"name": name})

    def delete_category(self, category_id: int) -> None:
        self._request("DELETE", f"/api/categories/{category_id}")

    def list_expenses(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        category_id: int | None = None,
    ) -> list[dict]:
        params: dict = {}
        if date_from is not None:
            params["date_from"] = date_from.isoformat()
        if date_to is not None:
            params["date_to"] = date_to.isoformat()
        if category_id is not None:
            params["category_id"] = category_id
        return self._request("GET", "/api/expenses", params=params)

    def create_expense(self, payload: dict) -> dict:
        return self._request("POST", "/api/expenses", json=payload)

    def update_expense(self, expense_id: int, payload: dict) -> dict:
        return self._request("PUT", f"/api/expenses/{expense_id}", json=payload)

    def delete_expense(self, expense_id: int) -> None:
        self._request("DELETE", f"/api/expenses/{expense_id}")

    def get_summary(self, *, date_from: date | None = None, date_to: date | None = None) -> dict:
        params: dict = {}
        if date_from is not None:
            params["date_from"] = date_from.isoformat()
        if date_to is not None:
            params["date_to"] = date_to.isoformat()
        return self._request("GET", "/api/summary", params=params)

    def _request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with httpx.Client(base_url=self.base_url, timeout=10.0) as client:
                response = client.request(method, path, json=json, params=params, headers=headers)
        except httpx.RequestError as exc:
            raise ApiError(0, "Could not reach the API. Start the backend and try again.") from exc
        if response.status_code >= 400:
            raise ApiError(response.status_code, _detail(response))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or "Request failed"
    detail = body.get("detail", "Request failed")
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                location = " ".join(str(part) for part in item.get("loc", []) if part != "body")
                message = item.get("msg", "Invalid value")
                parts.append(f"{location}: {message}" if location else message)
            else:
                parts.append(str(item))
        return "; ".join(parts) or "Request failed"
    return str(detail)
