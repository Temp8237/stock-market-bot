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
from monitoring import BotMonitor
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

        # Monitoring helper to persist status between runs
        self.monitor = BotMonitor('real_stock_market_bot')
        self.monitor.record_event('info', 'RealStockMarketBot initialization started')

        # Track whether we've already emitted certain warnings
        self._alpha_warning_logged = False
        self._news_warning_logged = False

        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            self.monitor.record_event(
                'error',
                'Missing X API credentials during initialization',
            )
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
            self.monitor.record_event('error', 'Failed to initialize X client', {'error': str(e)})
            raise

        # Major stocks to track
        self.major_stocks = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

        logging.info("Real Stock Market Bot initialized successfully")
        self.monitor.record_event(
            'success',
            'RealStockMarketBot initialized successfully',
            {'tracked_stocks': self.major_stocks},
        )
    
    def get_stock_data_alpha_vantage(self, symbol):
        """Get real stock data from Alpha Vantage"""
        if not self.alpha_vantage_key:
            logging.warning("No Alpha Vantage API key - using sample data")
            if not self._alpha_warning_logged:
                self.monitor.record_event(
                    'warning',
                    'Alpha Vantage API key missing; using sample data',
                )
                self._alpha_warning_logged = True
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
            self.monitor.record_event(
                'error',
                f'Network error retrieving {symbol} data from Alpha Vantage',
                {'symbol': symbol, 'error': str(exc)},
            )
            return None

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid JSON response for {symbol}: {exc}")
            self.monitor.record_event(
                'error',
                f'Invalid JSON response for {symbol} from Alpha Vantage',
                {'symbol': symbol, 'error': str(exc)},
            )
            return None

        if data.get('Note'):
            logging.warning(
                "Alpha Vantage API limit reached while fetching data for %s",
                symbol,
            )
            self.monitor.record_event(
                'warning',
                'Alpha Vantage API limit reached',
                {'symbol': symbol},
            )
            return None

        if data.get('Error Message'):
            logging.error(
                "Alpha Vantage returned an error for %s data request: %s",
                symbol,
                data['Error Message'],
            )
            self.monitor.record_event(
                'error',
                'Alpha Vantage returned an error response',
                {'symbol': symbol, 'message': data['Error Message']},
            )
            return None

        time_series = data.get('Time Series (Daily)')
        if not isinstance(time_series, dict):
            logging.warning(f"No time series data available for {symbol}")
            self.monitor.record_event(
                'warning',
                'No time series data available in Alpha Vantage response',
                {'symbol': symbol},
            )
            return None

        dates = sorted(time_series.keys(), reverse=True)
        if len(dates) < 2:
            logging.warning(f"Not enough data points returned for {symbol}")
            self.monitor.record_event(
                'warning',
                'Alpha Vantage returned insufficient data points',
                {'symbol': symbol, 'dates_returned': len(dates)},
            )
            return None

        today, yesterday = dates[0], dates[1]
        try:
            today_close = float(time_series[today]['4. close'])
            yesterday_close = float(time_series[yesterday]['4. close'])
        except (KeyError, TypeError, ValueError) as exc:
            logging.error(f"Invalid price data for {symbol}: {exc}")
            self.monitor.record_event(
                'error',
                'Alpha Vantage returned invalid price data',
                {'symbol': symbol, 'error': str(exc)},
            )
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
            if not self._news_warning_logged:
                self.monitor.record_event(
                    'warning',
                    'News API key missing; using sample headlines',
                )
                self._news_warning_logged = True
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
            self.monitor.record_event(
                'warning',
                'Network error retrieving NewsAPI headlines',
                {'symbol': symbol, 'error': str(exc)},
            )
            return self.get_sample_news(symbol)

        try:
            data = response.json()
        except ValueError as exc:
            logging.error(f"Invalid news response for {symbol}: {exc}")
            self.monitor.record_event(
                'warning',
                'Invalid JSON response from NewsAPI',
                {'symbol': symbol, 'error': str(exc)},
            )
            return self.get_sample_news(symbol)

        if data.get('status') != 'ok':
            logging.warning(
                "News API returned status '%s' for %s", data.get('status'), symbol
            )
            self.monitor.record_event(
                'warning',
                'NewsAPI returned a non-ok status',
                {'symbol': symbol, 'status': data.get('status')},
            )
            return self.get_sample_news(symbol)

        articles = data.get('articles') or []
        if not articles:
            logging.warning(f"No news articles found for {symbol}")
            self.monitor.record_event(
                'warning',
                'No NewsAPI articles found',
                {'symbol': symbol},
            )
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
        self.monitor.record_event(
            'warning',
            'NewsAPI articles lacked titles',
            {'symbol': symbol},
        )
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
    
    def get_market_data_with_news(self):
        """Get real market data with news"""
        market_data = {}
        real_symbols = []
        sample_symbols = []

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
                real_symbols.append(symbol)
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
                    sample_symbols.append(symbol)

            # Rate limiting - wait between requests
            time.sleep(1)

        if real_symbols:
            self.monitor.record_event(
                'info',
                'Fetched live market data',
                {'symbols': real_symbols},
            )
        if sample_symbols:
            self.monitor.record_event(
                'warning',
                'Using sample market data for symbols',
                {'symbols': sample_symbols},
            )

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
    
    def format_market_update(self, top_movers, is_morning=True):
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
        summary = ""
        if gains and losses:
            summary = f"📈 Gainers: {len(gains)} | 📉 Losers: {len(losses)}"
        elif gains:
            summary = "📈 Market showing positive momentum"
        elif losses:
            summary = "📉 Market showing downward pressure"

        # Randomized templates
        templates = [
            f"📊 {time_of_day} Market Update\n\n🔥 Top Movers Today:\n{movers_str}\n\n{summary}\n⏰ {now_str}",
            f"{time_of_day} Recap: Who moved the market?\n{movers_str}\n{summary}\n⏰ {now_str}",
            f"{time_of_day} movers: {', '.join([m['name'] for m in top_movers])}\n\n{movers_str}\n{summary}\n⏰ {now_str}",
            f"{time_of_day} Stock Highlights:\n{movers_str}\n{summary}\n⏰ {now_str}",
            f"{time_of_day} - {now_str}\nBiggest swings:\n{movers_str}\n{summary}",
            f"{time_of_day} Market Movers:\n{movers_str}\n{summary}\n⏰ {now_str}",
            f"{time_of_day} - Top 3 movers:\n{movers_str}\n{summary}\n⏰ {now_str}"
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
        update_label = 'morning' if is_morning else 'evening'
        try:
            logging.info(f"Starting {'morning' if is_morning else 'evening'} market update")
            self.monitor.record_event('info', f'Starting {update_label} market update')

            # Get market data with news
            market_data = self.get_market_data_with_news()

            # Analyze changes
            top_movers = self.analyze_market_changes(market_data)

            # Format message
            message = self.format_market_update(top_movers, is_morning)

            run_metadata = {
                'symbols_with_data': list(market_data.keys()),
                'top_movers': [
                    {
                        'symbol': mover['symbol'],
                        'change_pct': mover['change_pct'],
                        'price': mover['price'],
                    }
                    for mover in top_movers
                ],
                'tweet_length': len(message),
            }

            # Post to X
            success = self.post_to_x(message)

            if success:
                logging.info("Market update completed successfully")
                self.monitor.record_run(
                    update_label,
                    'success',
                    'Market update posted to X',
                    run_metadata,
                )
            else:
                logging.error("Failed to post market update")
                self.monitor.record_run(
                    update_label,
                    'error',
                    'Failed to post market update',
                    run_metadata,
                )

        except Exception as e:
            logging.error(f"Error in market update: {e}")
            self.monitor.record_run(
                update_label,
                'error',
                f'Exception during {update_label} update',
                {'error': str(e)},
            )
    
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
        self.monitor.record_event('info', 'Scheduler started for RealStockMarketBot')

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
