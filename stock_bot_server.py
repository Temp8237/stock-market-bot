#!/usr/bin/env python3
"""
Server-Optimized Stock Market Bot
Runs on Railway or other cloud platforms
Uses cron-style scheduling instead of the schedule library
"""

import os
import time
import tweepy
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import json
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ServerStockMarketBot:
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
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError("Missing X API credentials in environment variables")
        
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

        logging.info("Server Stock Market Bot initialized successfully")

        # Track when we last posted updates to avoid duplicates if the
        # exact check time is missed due to the sleep interval
        self.last_morning_post = None
        self.last_evening_post = None
    
    def get_stock_data_alpha_vantage(self, symbol):
        """Get real stock data from Alpha Vantage"""
        if not self.alpha_vantage_key:
            logging.warning("No Alpha Vantage API key - using sample data")
            return None
        
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key,
                'outputsize': 'compact'
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'Time Series (Daily)' in data:
                time_series = data['Time Series (Daily)']
                dates = sorted(time_series.keys(), reverse=True)
                
                if len(dates) >= 2:
                    today = dates[0]
                    yesterday = dates[1]
                    
                    today_close = float(time_series[today]['4. close'])
                    yesterday_close = float(time_series[yesterday]['4. close'])
                    
                    change = today_close - yesterday_close
                    change_pct = (change / yesterday_close) * 100
                    
                    return {
                        'price': today_close,
                        'change': change,
                        'change_pct': change_pct,
                        'name': symbol
                    }
            
            logging.warning(f"No data available for {symbol}")
            return None
            
        except Exception as e:
            logging.error(f"Error getting data for {symbol}: {e}")
            return None
    
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
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == 'ok' and data.get('articles'):
                articles = data['articles']
                if articles:
                    # Get the most recent relevant article
                    for article in articles:
                        title = article.get('title', '')
                        if any(keyword in title.lower() for keyword in ['stock', 'earnings', 'revenue', 'growth', 'sales', 'profit']):
                            return title[:100] + "..." if len(title) > 100 else title
                    
                    # If no relevant article, use the first one
                    title = articles[0].get('title', '')
                    return title[:100] + "..." if len(title) > 100 else title
            
            logging.warning(f"No news found for {symbol}")
            return self.get_sample_news(symbol)
            
        except Exception as e:
            logging.error(f"Error getting news for {symbol}: {e}")
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
        """Post message to X"""
        try:
            # X has a 280 character limit
            if len(message) > 280:
                message = message[:277] + "..."
            
            response = self.client.create_tweet(text=message)
            logging.info("Successfully posted to X")
            return True
            
        except Exception as e:
            logging.error(f"Error posting to X: {e}")
            return False
    
    def run_market_update(self, is_morning=True):
        """Run the complete market update process"""
        try:
            logging.info(f"Starting {'morning' if is_morning else 'evening'} market update")
            
            # Get market data with news
            market_data = self.get_market_data_with_news()
            
            # Analyze changes
            top_movers = self.analyze_market_changes(market_data)
            
            # Format message
            message = self.format_market_update(top_movers, is_morning)
            
            # Post to X
            success = self.post_to_x(message)
            
            if success:
                logging.info("Market update completed successfully")
            else:
                logging.error("Failed to post market update")
                
        except Exception as e:
            logging.error(f"Error in market update: {e}")
    
    def should_post_morning_update(self):
        """Check if it's time for morning update (around 8 AM)"""
        now = datetime.now()
        if now.hour == 8 and now.minute < 5:
            # Only post once per day
            if self.last_morning_post != now.date():
                return True
        return False

    def should_post_evening_update(self):
        """Check if it's time for evening update (around 8 PM)"""
        now = datetime.now()
        if now.hour == 20 and now.minute < 5:
            # Only post once per day
            if self.last_evening_post != now.date():
                return True
        return False
    
    def run_server_loop(self):
        """Main server loop that checks for posting times"""
        logging.info("Server bot started - checking for 8:00 AM and 8:00 PM updates")
        
        while True:
            try:
                now = datetime.now()
                
                # Check for morning update (8 AM)
                if self.should_post_morning_update():
                    logging.info("Time for morning update!")
                    self.run_market_update(is_morning=True)
                    self.last_morning_post = now.date()
                    time.sleep(60)  # Wait a minute to avoid duplicate posts
                
                # Check for evening update (8 PM)
                elif self.should_post_evening_update():
                    logging.info("Time for evening update!")
                    self.run_market_update(is_morning=False)
                    self.last_evening_post = now.date()
                    time.sleep(60)  # Wait a minute to avoid duplicate posts
                
                # Log status every hour
                elif now.minute == 0:
                    logging.info(f"Bot is running - {now.strftime('%Y-%m-%d %H:%M')}")
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except Exception as e:
                logging.error(f"Error in server loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

def main():
    """Main function to run the server bot"""
    try:
        bot = ServerStockMarketBot()
        bot.run_server_loop()
    except Exception as e:
        logging.error(f"Failed to start server bot: {e}")

if __name__ == "__main__":
    main() 