"""
Library to fetch reimbursable transactions from YNAB, and then request payment to relevant parties via Venmo.
"""

import requests


def fetch_relevant_transactions(ynab)