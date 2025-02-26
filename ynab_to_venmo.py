"""
Library to fetch reimbursable transactions from YNAB, and then request payment to relevant parties via Venmo.
"""

import collections
import dataclasses
import datetime
import pathlib
import json
import requests

@dataclasses.dataclass(frozen=True)
class Secrets:
    token: str # YNAB API token
    budget_id: str # YNAB budget ID
    reimbursement_category_id: str # YNAB category ID for reimbursements

_SECRETS_FILE = pathlib.Path("secrets/secrets.txt")

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Transaction:
    id: str
    parent_id: Optional[str]
    date: str
    amount: int
    category_id: Optional[str]
    category_name: Optional[str]
    description: Optional[str]
    payee_name: str

@dataclass
class Data:
    transactions: List[Transaction]

@dataclass
class Root:
    data: Data

def parse_json(json_str: str) -> Root:
    data_dict = json.loads(json_str)
    transactions = []
    for txn in data_dict['data']['transactions']:
        transaction = Transaction(
            id=txn['id'],
            parent_id=txn.get('parent_transaction_id'),
            date=txn['date'],
            amount=txn['amount'] / 1000.,  # Convert from cents to dollars
            category_id=txn.get('category_id'),
            category_name=txn.get('category_name'),
            description=txn.get('memo'),  # Assuming 'description' corresponds to 'memo'
            payee_name=txn['payee_name'],
        )
        if transaction.payee_name is None:
            print(txn)
        transactions.append(transaction)
    data = Data(transactions=transactions)
    return Root(data=data)

def read_secrets(path: pathlib.Path) -> str:
    with open(path, 'r') as file:
        file_string = file.read().strip()
    
    value_by_key = {}

    for line in file_string.splitlines():
        key, value = line.split('=')
        value_by_key[key.strip().lower()] = value.strip()
    return Secrets(**value_by_key)

def fetch_category_id(secrets: Secrets) -> str | None:
    url = f"https://api.ynab.com/v1/budgets/{secrets.budget_id}/categories"
    headers = {
        "Authorization": f"Bearer {secrets.token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        categories = response.json()
    for category in categories['data']['category_groups']:
        for category in category['categories']:
            if "Kelsey Repayment" in category['name']:
                return category['id']
    return None

def fetch_payee_name_by_transaction_id(secrets: Secrets, since_date: datetime.date) -> dict[str, str]:
    url = f"https://api.ynab.com/v1/budgets/{secrets.budget_id}/transactions?since_date={since_date.isoformat()}"
    headers = {
        "Authorization": f"Bearer {secrets.token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        transactions = response.json()
    parsed_data = parse_json(json.dumps(transactions))
    payee_name_by_transaction_id = {}
    for transaction in parsed_data.data.transactions:
        if transaction.payee_name is not None:
            payee_name_by_transaction_id[transaction.id] = transaction.payee_name
    return payee_name_by_transaction_id

def fetch_relevant_transactions(since_date: datetime.date | None = None) -> None:
    secrets = read_secrets(_SECRETS_FILE)
    since_date = since_date or datetime.date.today() - datetime.timedelta(days=91)
    category_id = fetch_category_id(secrets)
    if category_id is None:
        raise ValueError("No category ID found for Kelsey Repayment")
    
    url = f"https://api.ynab.com/v1/budgets/{secrets.budget_id}/categories/{category_id}/transactions?since_date={since_date.isoformat()}"
    headers = {
        "Authorization": f"Bearer {secrets.token}"
    }
    
    response = requests.get(url, headers=headers)
    
    payee_by_transaction_id = fetch_payee_name_by_transaction_id(secrets, since_date)
    print(payee_by_transaction_id)

    if response.status_code == 200:
        transactions = response.json()
        parsed_data = parse_json(json.dumps(transactions))
        print(len(parsed_data.data.transactions), "transactions found")
    
    for transaction in parsed_data.data.transactions:
        if "Kelsey Repayment" in transaction.category_name:
            payee_name = transaction.payee_name
            if payee_name is None:
                payee_name = payee_by_transaction_id.get(transaction.parent_id)
            print(f"Date: {transaction.date}, Amount: ${transaction.amount}, Payee: {payee_name}")

if __name__ == "__main__":
    fetch_relevant_transactions()