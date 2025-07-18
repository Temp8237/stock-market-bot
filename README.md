# Stock Market Bot for X (Twitter)

A Python bot that automatically posts stock market updates to X (Twitter) at 8:00 AM and 8:00 PM daily. The bot tracks major market indices and stocks, analyzes the biggest market movers, and posts formatted updates.

## Features

- 📊 Tracks major market indices (S&P 500, Dow Jones, NASDAQ, Russell 2000)
- 🏢 Monitors major stocks (Apple, Microsoft, Google, Amazon, Tesla, NVIDIA, Meta, Netflix)
- ⏰ Automated posting at 8:00 AM and 8:00 PM
- 📈 Identifies biggest market movers (gainers and losers)
- 📱 Posts formatted updates to X (Twitter)
- 📝 Comprehensive logging
- 🔄 Automatic retries for API requests

## Prerequisites

- Python 3.7 or higher
- X (Twitter) Developer Account
- X API credentials

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get X API Credentials

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new app or use an existing one
3. Generate API keys and access tokens
4. Make sure your app has "Read and Write" permissions

### 3. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp env_example.txt .env
   ```

2. Edit the `.env` file with your X API credentials:
   ```
   X_API_KEY=your_actual_api_key
   X_API_SECRET=your_actual_api_secret
   X_ACCESS_TOKEN=your_actual_access_token
   X_ACCESS_TOKEN_SECRET=your_actual_access_token_secret
   ```

### 4. Test the Bot

Run a test to make sure everything is working:

```bash
python stock_bot.py
```

The bot will start and schedule posts for 8:00 AM and 8:00 PM. You can stop it with Ctrl+C.

## Usage

### Running the Bot

```bash
python stock_bot.py
```

The bot will:
- Start the scheduler
- Run market updates at 8:00 AM and 8:00 PM
- Log all activities to `stock_bot.log`

### Running as a Service (Optional)

To run the bot continuously in the background:

#### On macOS/Linux:
```bash
nohup python stock_bot.py > bot_output.log 2>&1 &
```

#### Using systemd (Linux):
1. Create a service file: `/etc/systemd/system/stock-bot.service`
2. Enable and start the service:
   ```bash
   sudo systemctl enable stock-bot
   sudo systemctl start stock-bot
   ```

## What the Bot Posts

The bot posts formatted updates like this:

```
📊 Morning Market Update

🔥 Biggest Market Movers:
1. NVIDIA: +5.23% 📈
2. Tesla: -3.45% 📉
3. Apple: +2.18% 📈

📈 Gainers: 2 | 📉 Losers: 1

⏰ 2024-01-15 08:00
```

## Customization

### Adding More Stocks

Edit the `major_stocks` list in `stock_bot.py`:

```python
self.major_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'YOUR_STOCK']
```

### Changing Post Times

Edit the scheduler in the `start_scheduler` method:

```python
schedule.every().day.at("09:00").do(self.morning_update)  # Change to 9 AM
schedule.every().day.at("17:00").do(self.evening_update)  # Change to 5 PM
```

### Modifying Message Format

Edit the `format_market_update` method to change how posts look.

## Troubleshooting

### Common Issues

1. **"Missing X API credentials"**
   - Make sure your `.env` file exists and has all required credentials
   - Verify your API keys are correct

2. **"Error posting to X"**
   - Check your X API permissions (need "Read and Write")
   - Verify your access tokens are correct
   - Check if you've hit rate limits

3. **"Error fetching market data"**
   - Check your internet connection
   - Yahoo Finance API might be temporarily unavailable
   - The bot automatically retries failed requests, but persistent errors will be logged

### Logs

Check the `stock_bot.log` file for detailed error messages and debugging information.

## Security Notes

- Never commit your `.env` file to version control
- Keep your API credentials secure
- Consider using environment variables in production

## Dependencies

- `tweepy`: X (Twitter) API wrapper
- `yfinance`: Yahoo Finance data
- `schedule`: Task scheduling
- `pandas`: Data manipulation
- `python-dotenv`: Environment variable management

## License

This project is open source and available under the MIT License.

## Contributing

Feel free to submit issues and enhancement requests! 