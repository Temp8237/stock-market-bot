#!/usr/bin/env python3
"""
Revenue Report Bot
Fetches latest quarterly revenue for tracked companies and posts
summaries to X when new earnings are released.
"""

import os
import logging
from datetime import datetime

import tweepy
from dotenv import load_dotenv
from utils import create_session, post_with_retry
import requests

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_bot.log'),
        logging.StreamHandler()
    ]
)


class RevenueReportBot:
    def __init__(self):
        self.api_key = os.getenv('X_API_KEY')
        self.api_secret = os.getenv('X_API_SECRET')
        self.access_token = os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')

        if not all([
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_token_secret,
        ]):
            raise ValueError("Missing X API credentials in .env file")

        if not self.alpha_vantage_key:
            raise ValueError("Missing ALPHA_VANTAGE_API_KEY in .env file")

        self.session = create_session()

        try:
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )
        except Exception as e:
            logging.error(f"Could not initialize X client: {e}")
            raise

        # Map tickers to company names
        self.stocks = {
            'AAPL': 'Apple',
            'MSFT': 'Microsoft',
            'GOOGL': 'Google',
            'TSLA': 'Tesla',
            'NVDA': 'NVIDIA',
        }

        logging.info("Revenue Report Bot initialized successfully")

    def fetch_latest_earnings(self, symbol: str):
        """Fetch the latest earnings entry for a symbol."""
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'EARNINGS',
            'symbol': symbol,
            'apikey': self.alpha_vantage_key,
        }
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.error(f"Error fetching earnings for {symbol}: {exc}")
            return None

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid earnings response for {symbol}: {exc}")
            return None

        if data.get('Note'):
            logging.warning(
                "Alpha Vantage API limit reached while fetching earnings for %s",
                symbol,
            )
            return None

        if data.get('Error Message'):
            logging.error(
                "Alpha Vantage returned an error for %s earnings request: %s",
                symbol,
                data['Error Message'],
            )
            return None

        quarterly = data.get('quarterlyEarnings')
        if not isinstance(quarterly, list) or not quarterly:
            logging.warning("No quarterly earnings data available for %s", symbol)
            return None

        return quarterly[0]

    def fetch_quarterly_revenues(self, symbol: str):
        """Return current and previous quarter revenues and fiscal date."""
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'INCOME_STATEMENT',
            'symbol': symbol,
            'apikey': self.alpha_vantage_key,
        }
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.error(f"Error fetching income statement for {symbol}: {exc}")
            return None, None, None

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid income statement response for {symbol}: {exc}")
            return None, None, None

        if data.get('Note'):
            logging.warning(
                "Alpha Vantage API limit reached while fetching income statement for %s",
                symbol,
            )
            return None, None, None

        if data.get('Error Message'):
            logging.error(
                "Alpha Vantage returned an error for %s income statement request: %s",
                symbol,
                data['Error Message'],
            )
            return None, None, None

        reports = data.get('quarterlyReports', [])
        if len(reports) < 2:
            logging.warning("Not enough quarterly reports available for %s", symbol)
            return None, None, None

        current = reports[0]
        previous = reports[1]

        current_revenue = self._parse_revenue_value(
            current.get('totalRevenue'), symbol, "current"
        )
        previous_revenue = self._parse_revenue_value(
            previous.get('totalRevenue'), symbol, "previous"
        )
        fiscal_date = current.get('fiscalDateEnding')

        if current_revenue is None or previous_revenue is None:
            return None, None, fiscal_date

        return current_revenue, previous_revenue, fiscal_date

    @staticmethod
    def _parse_revenue_value(value, symbol: str, period: str):
        """Convert Alpha Vantage revenue strings to floats safely."""
        if value in (None, "", "None"):
            logging.warning("Missing %s revenue value for %s", period, symbol)
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            logging.warning(
                "Unable to parse %s revenue value '%s' for %s", period, value, symbol
            )
            return None

    def format_message(
        self, name: str, fiscal_date: str, revenue: float, prev_revenue: float
    ) -> str:
        """Format the revenue report message."""
        change_pct = 0.0
        if prev_revenue:
            change_pct = (revenue - prev_revenue) / prev_revenue * 100
        emoji = "📈" if change_pct >= 0 else "📉"
        revenue_b = revenue / 1_000_000_000
        fiscal_period = fiscal_date or "Unknown"
        message = (
            f"{name} Revenue Report\n\n"
            f"Quarter ending {fiscal_period}: ${revenue_b:.2f}B {emoji}\n"
            f"Change vs prev quarter: {change_pct:+.2f}%"
        )
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d')}"
        if len(message) > 280:
            message = message[:277] + "..."
        return message

    def post_to_x(self, message: str) -> bool:
        return post_with_retry(self.client, message)

    def check_and_post_reports(self):
        """Check for new earnings reports and post revenue summaries."""
        today = datetime.now().date()
        for symbol, name in self.stocks.items():
            earnings = self.fetch_latest_earnings(symbol)
            if not earnings:
                continue
            try:
                report_date = datetime.strptime(
                    earnings['reportedDate'], '%Y-%m-%d'
                ).date()
            except Exception:
                continue
            if abs((today - report_date).days) <= 1:
                revenue, prev_revenue, fiscal_date = self.fetch_quarterly_revenues(
                    symbol
                )
                if revenue is None or prev_revenue is None:
                    continue
                message = self.format_message(name, fiscal_date, revenue, prev_revenue)
                self.post_to_x(message)


def main():
    try:
        bot = RevenueReportBot()
        bot.check_and_post_reports()
    except Exception as e:
        logging.error(f"Failed to run revenue report bot: {e}")


if __name__ == "__main__":
    main()
