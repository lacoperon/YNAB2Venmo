"""
Library to fetch reimbursable transactions from YNAB, and then request payment to relevant parties via Venmo.
"""

import requests

_TOKEN_FILE = "secrets/ynab_token.txt"

def read_ynab_token() -> None:
    """
    Reads the YNAB token from a file.
    """
    with open(_TOKEN_FILE, 'r') as file:
        return file.read().strip()
    



def fetch_relevant_transactions(ynab)