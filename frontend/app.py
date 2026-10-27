"""Streamlit UI. All data goes through the FastAPI backend."""

import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from api_client import ApiError, ExpenseApi

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(page_title="Expense Tracker", layout="wide")


def format_money(value) -> str:
    return f"{Decimal(str(value)):,.2f}"


def build_api() -> ExpenseApi:
    base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
    return ExpenseApi(base_url, st.session_state.get("token"))


def show_flash() -> None:
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)


def call(api_fn, *args, **kwargs):
    try:
        return True, api_fn(*args, **kwargs)
    except ApiError as exc:
        if exc.status_code == 401 and st.session_state.get("token"):
            st.session_state.token = None
            st.session_state.auth_message = "Your session has ended. Please log in again."
            st.rerun()
        return False, exc.detail


def expense_payload(amount, expense_date, category_id, description) -> dict:
    return {
        "amount": f"{amount:.2f}",
        "expense_date": expense_date.isoformat(),
        "category_id": int(category_id),
        "description": description,
    }


def init_state() -> None:
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("username", None)


def login_screen(api: ExpenseApi) -> None:
    st.title("Expense Tracker")
    st.write("Sign in with the account created during database setup.")
    notice = st.session_state.pop("auth_message", None)
    if notice:
        st.warning(notice)
    left, _right = st.columns(2)
    with left:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
    if not submitted:
        return
    try:
        token = api.login(username, password)
    except ApiError as exc:
        st.error(exc.detail)
        return
    st.session_state.token = token
    st.session_state.username = username.strip()
    st.rerun()


def ensure_session(api: ExpenseApi) -> bool:
    if not st.session_state.get("token"):
        return False
    try:
        profile = api.me()
    except ApiError as exc:
        if exc.status_code == 401:
            st.session_state.token = None
            st.session_state.auth_message = "Your session has ended. Please log in again."
            return False
        st.error(exc.detail)
        st.stop()
    st.session_state.username = profile["username"]
    return True


def logout(api: ExpenseApi) -> None:
    try:
        api.logout()
    except ApiError:
        pass
    st.session_state.token = None
    st.session_state.username = None
    st.rerun()


def date_filters(key_prefix: str) -> tuple[date, date] | None:
    default_from = date(2000, 1, 1)
    default_to = date.today() + timedelta(days=365)
    start, end = st.columns(2)
    date_from = start.date_input("From", value=default_from, key=f"{key_prefix}-from")
    date_to = end.date_input("To", value=default_to, key=f"{key_prefix}-to")
    if date_from > date_to:
        st.error("From must be on or before To.")
        return None
    return date_from, date_to


def expenses_page(api: ExpenseApi) -> None:
    st.header("Expenses")
    show_flash()
    ok, categories = call(api.list_categories)
    if not ok:
        st.error(categories)
        return
    if not categories:
        st.error("No categories are available.")
        return

    category_names = {item["id"]: item["name"] for item in categories}
    filter_dates = date_filters("expenses")
    selected_category = st.selectbox(
        "Category filter",
        options=["All", *category_names.keys()],
        format_func=lambda value: "All categories" if value == "All" else category_names[value],
    )
    if filter_dates is None:
        return
    date_from, date_to = filter_dates
    category_id = None if selected_category == "All" else int(selected_category)
    ok, expenses = call(
        api.list_expenses,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
    )
    if not ok:
        st.error(expenses)
        return

    with st.form("add-expense"):
        st.subheader("Add expense")
        amount = st.number_input(
            "Amount",
            min_value=0.01,
            max_value=99999999.99,
            step=0.01,
            format="%.2f",
            key="add-amount",
        )
        expense_date = st.date_input("Date", value=date.today(), key="add-date")
        category = st.selectbox(
            "Category",
            options=list(category_names),
            format_func=lambda value: category_names[value],
            key="add-category",
        )
        description = st.text_input("Description", key="add-description")
        submitted = st.form_submit_button("Add expense", type="primary")
    if submitted:
        ok, result = call(
            api.create_expense,
            expense_payload(amount, expense_date, category, description),
        )
        if ok:
            st.session_state.flash = "Expense added."
            for key in ("add-amount", "add-date", "add-category", "add-description"):
                st.session_state.pop(key, None)
            st.rerun()
        st.error(result)

    st.subheader("Recorded expenses")
    if not expenses:
        st.info("No expenses match these filters.")
        return

    st.dataframe(
        [
            {
                "Date": row["expense_date"],
                "Category": row["category_name"],
                "Amount": format_money(row["amount"]),
                "Description": row["description"],
            }
            for row in expenses
        ],
        hide_index=True,
    )

    labels = {
        row["id"]: f"{row['expense_date']} · {row['category_name']} · {format_money(row['amount'])} · {row['description']}"
        for row in expenses
    }
    selected_id = st.selectbox("Edit expense", options=list(labels), format_func=lambda value: labels[value])
    selected = next(row for row in expenses if row["id"] == selected_id)
    with st.form(f"edit-expense-{selected_id}"):
        edit_amount = st.number_input(
            "Amount",
            min_value=0.01,
            max_value=99999999.99,
            value=float(selected["amount"]),
            step=0.01,
            format="%.2f",
            key=f"amount-{selected_id}",
        )
        edit_date = st.date_input("Date", value=date.fromisoformat(selected["expense_date"]), key=f"date-{selected_id}")
        edit_category = st.selectbox(
            "Category",
            options=list(category_names),
            index=list(category_names).index(selected["category_id"])
            if selected["category_id"] in category_names
            else 0,
            format_func=lambda value: category_names[value],
            key=f"category-{selected_id}",
        )
        edit_description = st.text_input("Description", value=selected["description"], key=f"description-{selected_id}")
        save = st.form_submit_button("Save changes", type="primary")
    if save:
        ok, result = call(
            api.update_expense,
            selected_id,
            expense_payload(edit_amount, edit_date, edit_category, edit_description),
        )
        if ok:
            st.session_state.flash = "Expense updated."
            st.rerun()
        st.error(result)

    confirm = st.checkbox("Confirm delete", key=f"confirm-{selected_id}")
    if st.button("Delete expense", disabled=not confirm):
        ok, result = call(api.delete_expense, selected_id)
        if ok:
            st.session_state.flash = "Expense deleted."
            st.rerun()
        st.error(result)


def categories_page(api: ExpenseApi) -> None:
    st.header("Categories")
    show_flash()
    ok, categories = call(api.list_categories)
    if not ok:
        st.error(categories)
        return

    st.dataframe(
        [
            {
                "Name": category["name"],
                "Type": "Predefined" if category["is_predefined"] else "Custom",
            }
            for category in categories
        ],
        hide_index=True,
    )

    with st.form("add-category"):
        st.subheader("Add a custom category")
        name = st.text_input("Category name", key="new-category-name")
        submitted = st.form_submit_button("Add category", type="primary")
    if submitted:
        ok, result = call(api.create_category, name)
        if ok:
            st.session_state.flash = "Category added."
            st.session_state.pop("new-category-name", None)
            st.rerun()
        st.error(result)

    custom = [category for category in categories if not category["is_predefined"]]
    if not custom:
        st.info("Predefined categories stay in the list. Custom categories you add can be deleted when unused.")
        return

    labels = {category["id"]: category["name"] for category in custom}
    selected_id = st.selectbox("Custom category", options=list(labels), format_func=lambda value: labels[value])
    confirm = st.checkbox("Confirm delete", key="confirm-category")
    if st.button("Delete category", disabled=not confirm):
        ok, result = call(api.delete_category, selected_id)
        if ok:
            st.session_state.flash = "Category deleted."
            st.rerun()
        st.error(result)


def summary_page(api: ExpenseApi) -> None:
    st.header("Spending summary")
    show_flash()
    filter_dates = date_filters("summary")
    if filter_dates is None:
        return
    date_from, date_to = filter_dates
    ok, summary = call(api.get_summary, date_from=date_from, date_to=date_to)
    if not ok:
        st.error(summary)
        return

    total_col, count_col = st.columns(2)
    total_col.metric("Total spending", format_money(summary["total"]))
    count_col.metric("Expenses", summary["expense_count"])

    breakdown = summary["by_category"]
    if not breakdown:
        st.info("No spending in this date range.")
        return

    frame = pd.DataFrame(
        {
            "Category": [row["category_name"] for row in breakdown],
            "Total": [float(Decimal(str(row["total"]))) for row in breakdown],
        }
    )
    st.bar_chart(frame.set_index("Category"))
    st.dataframe(
        [
            {
                "Category": row["category_name"],
                "Total": format_money(row["total"]),
                "Expenses": row["count"],
            }
            for row in breakdown
        ],
        hide_index=True,
    )


def main() -> None:
    init_state()
    api = build_api()
    if not ensure_session(api):
        login_screen(build_api())
        return

    st.sidebar.title("Expense Tracker")
    st.sidebar.write(f"Signed in as {st.session_state.username}")
    page = st.sidebar.radio("Go to", ["Expenses", "Categories", "Summary"])
    if st.sidebar.button("Log out"):
        logout(api)

    if page == "Expenses":
        expenses_page(api)
    elif page == "Categories":
        categories_page(api)
    else:
        summary_page(api)


main()
