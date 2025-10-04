#!/usr/bin/env python3
"""
Real Stock Market Bot with Live Data and News
Uses Alpha Vantage for stock data and NewsAPI for news
"""

import os
import time
import schedule
import tweepy
import requests
from utils import create_session, post_with_retry
from datetime import datetime
from dotenv import load_dotenv
import logging
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_bot.log'),
        logging.StreamHandler()
    ]
)

class RealStockMarketBot:
    def __init__(self):
        """Initialize the bot with API credentials"""
        # X API credentials
        self.api_key = os.getenv('X_API_KEY')
        self.api_secret = os.getenv('X_API_SECRET')
        self.access_token = os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        
        # Alpha Vantage API key
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        
        # News API key
        self.news_api_key = os.getenv('NEWS_API_KEY')

        # HTTP session with retry logic for reliability
        self.session = create_session()
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError("Missing X API credentials in .env file")
        
        # Initialize X API v2 client
        try:
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
        except Exception as e:
            logging.error(f"Could not initialize X client: {e}")
            raise
        
        # Major stocks to track
        self.major_stocks = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

        # Cache for sector performance to avoid repeated parsing if requests fail
        self._last_sector_snapshot = None
        self._last_sector_timestamp = None
        
        logging.info("Real Stock Market Bot initialized successfully")
    
    def get_stock_data_alpha_vantage(self, symbol):
        """Get real stock data from Alpha Vantage"""
        if not self.alpha_vantage_key:
            logging.warning("No Alpha Vantage API key - using sample data")
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key,
                'outputsize': 'compact'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.error(f"Network error getting data for {symbol}: {exc}")
            return None

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid JSON response for {symbol}: {exc}")
            return None

        if data.get('Note'):
            logging.warning(
                "Alpha Vantage API limit reached while fetching data for %s",
                symbol,
            )
            return None

        if data.get('Error Message'):
            logging.error(
                "Alpha Vantage returned an error for %s data request: %s",
                symbol,
                data['Error Message'],
            )
            return None

        time_series = data.get('Time Series (Daily)')
        if not isinstance(time_series, dict):
            logging.warning(f"No time series data available for {symbol}")
            return None

        dates = sorted(time_series.keys(), reverse=True)
        if len(dates) < 2:
            logging.warning(f"Not enough data points returned for {symbol}")
            return None

        today, yesterday = dates[0], dates[1]
        try:
            today_close = float(time_series[today]['4. close'])
            yesterday_close = float(time_series[yesterday]['4. close'])
        except (KeyError, TypeError, ValueError) as exc:
            logging.error(f"Invalid price data for {symbol}: {exc}")
            return None

        change = today_close - yesterday_close
        change_pct = (change / yesterday_close) * 100 if yesterday_close else 0.0

        return {
            'price': today_close,
            'change': change,
            'change_pct': change_pct,
            'name': symbol
        }
    
    def get_news_for_stock(self, symbol):
        """Get real news for a stock from NewsAPI"""
        if not self.news_api_key:
            logging.warning("No News API key - using sample news")
            return self.get_sample_news(symbol)
        
        try:
            # Get company name for better news search
            company_names = {
                'AAPL': 'Apple',
                'MSFT': 'Microsoft',
                'GOOGL': 'Google',
                'TSLA': 'Tesla',
                'NVDA': 'NVIDIA'
            }
            
            company_name = company_names.get(symbol, symbol)
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'"{company_name}" OR "{symbol}"',
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 5,
                'apiKey': self.news_api_key
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.error(f"Network error getting news for {symbol}: {exc}")
            return self.get_sample_news(symbol)

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid news response for {symbol}: {exc}")
            return self.get_sample_news(symbol)

        if data.get('status') != 'ok':
            logging.warning(
                "News API returned status '%s' for %s", data.get('status'), symbol
            )
            return self.get_sample_news(symbol)

        articles = data.get('articles') or []
        if not articles:
            logging.warning(f"No news articles found for {symbol}")
            return self.get_sample_news(symbol)

        for article in articles:
            title = (article.get('title') or '').strip()
            lowered = title.lower()
            if any(
                keyword in lowered
                for keyword in ['stock', 'earnings', 'revenue', 'growth', 'sales', 'profit']
            ) and title:
                return title[:100] + "..." if len(title) > 100 else title

        title = (articles[0].get('title') or '').strip()
        if title:
            return title[:100] + "..." if len(title) > 100 else title

        logging.warning(f"Articles lacked titles for {symbol}")
        return self.get_sample_news(symbol)
    
    def get_sample_news(self, symbol):
        """Get sample news when API is not available"""
        sample_news = {
            'AAPL': "📱 Apple reports strong iPhone sales growth",
            'MSFT': "☁️ Microsoft Azure cloud revenue surges",
            'GOOGL': "🔍 Google search advertising shows recovery",
            'TSLA': "⚡ Tesla Model Y sales exceed expectations",
            'NVDA': "🚀 NVIDIA AI chip demand continues strong"
        }
        return sample_news.get(symbol, f"📈 {symbol} shows positive momentum")
    
    def get_sector_performance(self):
        """Get top performing and lagging sectors from Alpha Vantage."""
        if not self.alpha_vantage_key:
            logging.warning("No Alpha Vantage API key - sector data unavailable")
            return self._last_sector_snapshot

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'SECTOR',
                'apikey': self.alpha_vantage_key
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.error(f"Network error fetching sector performance: {exc}")
            return self._last_sector_snapshot

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid sector response: {exc}")
            return self._last_sector_snapshot

        realtime = data.get('Rank A: Real-Time Performance')
        if not isinstance(realtime, dict):
            logging.warning("Sector performance data missing from Alpha Vantage response")
            return self._last_sector_snapshot

        try:
            parsed = []
            for sector, value in realtime.items():
                stripped = value.replace('%', '').strip()
                performance = float(stripped)
                parsed.append({'sector': sector, 'performance': performance})
        except (ValueError, AttributeError) as exc:
            logging.error(f"Failed to parse sector performance values: {exc}")
            return self._last_sector_snapshot

        if not parsed:
            logging.warning("Sector performance list empty after parsing")
            return self._last_sector_snapshot

        parsed.sort(key=lambda x: x['performance'], reverse=True)
        snapshot = {
            'best': parsed[0],
            'worst': parsed[-1],
            'retrieved_at': data.get('Meta Data', {}).get('Last Refreshed')
        }

        self._last_sector_snapshot = snapshot
        self._last_sector_timestamp = datetime.now()
        logging.info(
            "Sector leaders: %s (%.2f%%), laggards: %s (%.2f%%)",
            snapshot['best']['sector'],
            snapshot['best']['performance'],
            snapshot['worst']['sector'],
            snapshot['worst']['performance']
        )
        return snapshot

    def get_market_data_with_news(self):
        """Get real market data with news"""
        market_data = {}
        
        for symbol in self.major_stocks:
            logging.info(f"Fetching data for {symbol}...")
            
            # Get stock data
            stock_data = self.get_stock_data_alpha_vantage(symbol)
            
            if stock_data:
                # Get news for this stock
                news = self.get_news_for_stock(symbol)
                
                market_data[symbol] = {
                    **stock_data,
                    'news': news
                }
                
                logging.info(f"✅ {symbol}: ${stock_data['price']:.2f} ({stock_data['change_pct']:+.2f}%)")
            else:
                # Use sample data if no real data available
                sample_data = {
                    'AAPL': {'price': 150.25, 'change_pct': 2.5, 'name': 'Apple'},
                    'MSFT': {'price': 300.50, 'change_pct': 1.8, 'name': 'Microsoft'},
                    'GOOGL': {'price': 120.75, 'change_pct': -1.2, 'name': 'Google'},
                    'TSLA': {'price': 250.00, 'change_pct': 3.5, 'name': 'Tesla'},
                    'NVDA': {'price': 450.25, 'change_pct': 5.2, 'name': 'NVIDIA'}
                }
                
                if symbol in sample_data:
                    news = self.get_news_for_stock(symbol)
                    market_data[symbol] = {
                        **sample_data[symbol],
                        'news': news
                    }
                    logging.info(f"⚠️ {symbol}: Using sample data")
            
            # Rate limiting - wait between requests
            time.sleep(1)
        
        return market_data
    
    def analyze_market_changes(self, market_data):
        """Analyze market data and identify biggest changes"""
        if not market_data:
            return []

        # Find biggest gainers and losers
        changes = []
        for symbol, data in market_data.items():
            changes.append({
                'symbol': symbol,
                'name': data['name'],
                'change_pct': data['change_pct'],
                'price': data['price'],
                'news': data.get('news', '')
            })
        
        # Sort by absolute change percentage
        changes.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        
        # Get top 3 biggest movers
        top_movers = changes[:3]

        return top_movers

    def compute_market_breadth(self, market_data):
        """Compute aggregate stats like advancers, decliners, and average change."""
        if not market_data:
            return None

        total = len(market_data)
        advancers = sum(1 for item in market_data.values() if item['change_pct'] > 0)
        decliners = sum(1 for item in market_data.values() if item['change_pct'] < 0)
        unchanged = total - advancers - decliners
        avg_change = sum(item['change_pct'] for item in market_data.values()) / total if total else 0.0

        return {
            'total': total,
            'advancers': advancers,
            'decliners': decliners,
            'unchanged': unchanged,
            'average_change': avg_change
        }

    def format_market_update(self, top_movers, is_morning=True, market_summary=None, sector_summary=None):
        """Format market update for X post with randomized templates"""
        time_of_day = "Morning" if is_morning else "Evening"
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        if not top_movers:
            return f"📊 {time_of_day} Market Update\n\nUnable to fetch market data at this time.\n\n⏰ {now_str}"

        # Prepare data for template
        movers_lines = []
        for i, mover in enumerate(top_movers, 1):
            emoji = "📈" if mover['change_pct'] > 0 else "📉"
            movers_lines.append(f"{i}. {mover['name']}: {mover['change_pct']:+.2f}% {emoji}\n   {mover.get('news','')[:40]}{'...' if len(mover.get('news',''))>40 else ''}")
        movers_str = "\n".join(movers_lines)
        gains = [m for m in top_movers if m['change_pct'] > 0]
        losses = [m for m in top_movers if m['change_pct'] < 0]
        summary_lines = []
        if gains and losses:
            summary_lines.append(f"📈 Gainers: {len(gains)} | 📉 Losers: {len(losses)}")
        elif gains:
            summary_lines.append("📈 Market showing positive momentum")
        elif losses:
            summary_lines.append("📉 Market showing downward pressure")

        if market_summary and market_summary.get('total'):
            breadth_line = (
                f"Breadth: {market_summary['advancers']}/{market_summary['total']} adv"
            )
            if market_summary['decliners']:
                breadth_line += f", {market_summary['decliners']} dec"
            if market_summary['unchanged']:
                breadth_line += f", {market_summary['unchanged']} flat"
            summary_lines.append(breadth_line)

            avg_change = market_summary.get('average_change')
            if avg_change is not None:
                summary_lines.append(f"Avg move: {avg_change:+.2f}%")

        if sector_summary:
            best = sector_summary.get('best')
            worst = sector_summary.get('worst')
            if best and worst:
                summary_lines.append(
                    f"Sectors: {best['sector']} {best['performance']:+.2f}% | "
                    f"{worst['sector']} {worst['performance']:+.2f}%"
                )

        summary_block = "\n".join(summary_lines) if summary_lines else "No additional metrics available"

        # Randomized templates
        templates = [
            f"📊 {time_of_day} Market Update\n\n🔥 Top Movers Today:\n{movers_str}\n\n{summary_block}\n⏰ {now_str}",
            f"{time_of_day} Recap: Who moved the market?\n{movers_str}\n{summary_block}\n⏰ {now_str}",
            f"{time_of_day} movers: {', '.join([m['name'] for m in top_movers])}\n\n{movers_str}\n{summary_block}\n⏰ {now_str}",
            f"{time_of_day} Stock Highlights:\n{movers_str}\n{summary_block}\n⏰ {now_str}",
            f"{time_of_day} - {now_str}\nBiggest swings:\n{movers_str}\n{summary_block}",
            f"{time_of_day} Market Movers:\n{movers_str}\n{summary_block}\n⏰ {now_str}",
            f"{time_of_day} - Top 3 movers:\n{movers_str}\n{summary_block}\n⏰ {now_str}"
        ]
        message = random.choice(templates)
        # Truncate if needed
        if len(message) > 280:
            message = message[:277] + "..."
        return message
    
    def post_to_x(self, message):
        """Post message to X with retries"""
        if len(message) > 280:
            message = message[:277] + "..."

        # Debug: Print the message being posted
        print(f"📝 Message to post ({len(message)} chars):")
        print("-" * 40)
        print(message)
        print("-" * 40)

        return post_with_retry(self.client, message)
    
    def run_market_update(self, is_morning=True):
        """Run the complete market update process"""
        try:
            logging.info(f"Starting {'morning' if is_morning else 'evening'} market update")
            
            # Get market data with news
            market_data = self.get_market_data_with_news()
            
            # Analyze changes
            top_movers = self.analyze_market_changes(market_data)
            market_summary = self.compute_market_breadth(market_data)
            sector_summary = self.get_sector_performance()

            # Format message
            message = self.format_market_update(
                top_movers,
                is_morning,
                market_summary=market_summary,
                sector_summary=sector_summary
            )
            
            # Post to X
            success = self.post_to_x(message)
            
            if success:
                logging.info("Market update completed successfully")
            else:
                logging.error("Failed to post market update")
                
        except Exception as e:
            logging.error(f"Error in market update: {e}")
    
    def morning_update(self):
        """Morning market update (8 AM)"""
        self.run_market_update(is_morning=True)
    
    def evening_update(self):
        """Evening market update (8 PM)"""
        self.run_market_update(is_morning=False)
    
    def start_scheduler(self):
        """Start the scheduler to run updates at 8 AM and 8 PM"""
        schedule.every().day.at("08:00").do(self.morning_update)
        schedule.every().day.at("20:00").do(self.evening_update)
        
        logging.info("Scheduler started - updates scheduled for 8:00 AM and 8:00 PM")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function to run the bot"""
    try:
        bot = RealStockMarketBot()
        bot.start_scheduler()
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main() 
