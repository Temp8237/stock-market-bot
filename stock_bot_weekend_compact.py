#!/usr/bin/env python3
"""
Stock Market Bot for X (Twitter) - Compact Weekend Version
Posts concise predictions on weekends with legal disclaimers
"""

import os
import time
import schedule
import tweepy
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import random
from utils import post_with_retry
from monitoring import BotMonitor

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

class CompactWeekendStockMarketBot:
    def __init__(self):
        """Initialize the bot with X API v2 credentials"""
        self.api_key = os.getenv('X_API_KEY')
        self.api_secret = os.getenv('X_API_SECRET')
        self.access_token = os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

        # Monitoring helper to keep track of weekend updates
        self.monitor = BotMonitor('weekend_stock_market_bot')
        self.monitor.record_event('info', 'CompactWeekendStockMarketBot initialization started')

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

        logging.info("Compact Weekend Stock Market Bot initialized successfully")
        self.monitor.record_event(
            'success',
            'CompactWeekendStockMarketBot initialized successfully',
            {'tracked_stocks': self.major_stocks},
        )
    
    def is_weekend(self):
        """Check if it's currently weekend"""
        now = datetime.now()
        return now.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    def get_weekend_predictions(self):
        """Generate weekend market predictions"""
        predictions = {
            'AAPL': {
                'name': 'Apple',
                'prediction': random.choice([
                    'iPhone 16 pre-orders could drive momentum',
                    'MacBook sales expected to remain strong',
                    'Services revenue growth likely to continue'
                ]),
                'sentiment': random.choice(['bullish', 'neutral', 'cautious'])
            },
            'MSFT': {
                'name': 'Microsoft',
                'prediction': random.choice([
                    'Azure cloud growth expected to accelerate',
                    'AI integration could boost Office subscriptions',
                    'Gaming division may see strong quarter'
                ]),
                'sentiment': random.choice(['bullish', 'neutral', 'cautious'])
            },
            'GOOGL': {
                'name': 'Google',
                'prediction': random.choice([
                    'Search ad revenue likely to show recovery',
                    'Android 15 adoption could boost ecosystem',
                    'Gemini AI features may drive engagement'
                ]),
                'sentiment': random.choice(['bullish', 'neutral', 'cautious'])
            },
            'TSLA': {
                'name': 'Tesla',
                'prediction': random.choice([
                    'Model Y demand expected to remain strong',
                    'Battery technology advances could boost margins',
                    'European expansion plans may accelerate'
                ]),
                'sentiment': random.choice(['bullish', 'neutral', 'cautious'])
            },
            'NVDA': {
                'name': 'NVIDIA',
                'prediction': random.choice([
                    'AI chip demand likely to continue surging',
                    'Gaming GPU sales expected to exceed estimates',
                    'Data center revenue could hit new records'
                ]),
                'sentiment': random.choice(['bullish', 'neutral', 'cautious'])
            }
        }
        return predictions
    
    def format_weekend_update(self, predictions, is_morning=True):
        """Format weekend market prediction update (compact version)"""
        time_of_day = "Morning" if is_morning else "Evening"
        
        # Create the main message (compact format)
        message = f"📊 {time_of_day} Market Predictions (Weekend)\n\n"
        message += "🔮 Key Stocks to Watch:\n"
        
        # Add top 2 predictions (shorter format)
        stocks = list(predictions.keys())[:2]
        for i, symbol in enumerate(stocks, 1):
            stock = predictions[symbol]
            emoji = "📈" if stock['sentiment'] == 'bullish' else "📊" if stock['sentiment'] == 'neutral' else "⚠️"
            message += f"{i}. {stock['name']}: {emoji}\n"
            message += f"   {stock['prediction']}\n"
        
        # Add market sentiment summary (shorter)
        bullish = [s for s in predictions.values() if s['sentiment'] == 'bullish']
        neutral = [s for s in predictions.values() if s['sentiment'] == 'neutral']
        cautious = [s for s in predictions.values() if s['sentiment'] == 'cautious']
        
        if bullish and not cautious:
            message += "\n📈 Positive sentiment"
        elif cautious and not bullish:
            message += "\n⚠️ Cautious sentiment"
        else:
            message += "\n📊 Mixed sentiment"
        
        # Add legal disclaimer (very short version)
        message += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        message += "\n\n⚠️ Not financial advice. Do your own research."
        
        return message
    
    def post_to_x(self, message):
        """Post message to X using v2 API with retries"""
        if len(message) > 280:
            # Truncate but keep disclaimer
            disclaimer = "\n\n⚠️ Not financial advice. Do your own research."
            max_content = 280 - len(disclaimer)
            message = message[:max_content] + disclaimer
        return post_with_retry(self.client, message)
    
    def run_weekend_update(self, is_morning=True):
        """Run the weekend prediction update process"""
        update_label = 'morning' if is_morning else 'evening'
        try:
            logging.info(f"Starting {'morning' if is_morning else 'evening'} weekend prediction update")
            self.monitor.record_event('info', f'Starting {update_label} weekend prediction update')

            # Generate predictions
            predictions = self.get_weekend_predictions()

            # Format message
            message = self.format_weekend_update(predictions, is_morning)

            run_metadata = {
                'predictions': [
                    {
                        'symbol': symbol,
                        'sentiment': details['sentiment'],
                    }
                    for symbol, details in predictions.items()
                ],
                'tweet_length': len(message),
            }

            # Post to X
            success = self.post_to_x(message)

            if success:
                logging.info("Weekend prediction update completed successfully")
                self.monitor.record_run(
                    update_label,
                    'success',
                    'Weekend prediction update posted to X',
                    run_metadata,
                )
            else:
                logging.error("Failed to post weekend prediction update")
                self.monitor.record_run(
                    update_label,
                    'error',
                    'Failed to post weekend prediction update',
                    run_metadata,
                )

        except Exception as e:
            logging.error(f"Error in weekend update: {e}")
            self.monitor.record_run(
                update_label,
                'error',
                f'Exception during {update_label} weekend update',
                {'error': str(e)},
            )
    
    def morning_update(self):
        """Morning update (8 AM) - handles both weekday and weekend"""
        if self.is_weekend():
            self.monitor.record_event('info', 'Weekend detected - running morning prediction update')
            self.run_weekend_update(is_morning=True)
        else:
            # For weekdays, use regular market data
            logging.info("Weekday detected - using regular market data")
            self.monitor.record_run(
                'morning',
                'skipped',
                'Weekend bot idle during weekday morning slot',
            )
            # You could import and use the regular bot here

    def evening_update(self):
        """Evening update (8 PM) - handles both weekday and weekend"""
        if self.is_weekend():
            self.monitor.record_event('info', 'Weekend detected - running evening prediction update')
            self.run_weekend_update(is_morning=False)
        else:
            # For weekdays, use regular market data
            logging.info("Weekday detected - using regular market data")
            self.monitor.record_run(
                'evening',
                'skipped',
                'Weekend bot idle during weekday evening slot',
            )
            # You could import and use the regular bot here
    
    def start_scheduler(self):
        """Start the scheduler to run updates at 8 AM and 8 PM"""
        schedule.every().day.at("08:00").do(self.morning_update)
        schedule.every().day.at("20:00").do(self.evening_update)

        logging.info("Compact weekend bot scheduler started - updates scheduled for 8:00 AM and 8:00 PM")
        self.monitor.record_event('info', 'Scheduler started for CompactWeekendStockMarketBot')

        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function to run the compact weekend bot"""
    try:
        bot = CompactWeekendStockMarketBot()
        bot.start_scheduler()
    except Exception as e:
        logging.error(f"Failed to start compact weekend bot: {e}")

if __name__ == "__main__":
    main()
