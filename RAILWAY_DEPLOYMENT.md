# 🚀 Railway Deployment Guide

## Quick Setup (5 minutes)

### 1. Create GitHub Repository
1. Go to [GitHub.com](https://github.com)
2. Create a new repository called `stock-market-bot`
3. Upload all files from this folder to the repository

### 2. Deploy to Railway
1. Go to [Railway.app](https://railway.app)
2. Sign up with your GitHub account
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `stock-market-bot` repository
5. Railway will automatically detect it's a Python app

### 3. Add Environment Variables
In your Railway project dashboard:
1. Go to "Variables" tab
2. Add these environment variables:

```
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_news_api_key
```

### 4. Deploy!
- Railway will automatically deploy your bot
- The bot will start running immediately
- Check the "Deployments" tab for logs

## ✅ What This Gives You

- **24/7 Bot Operation**: No need to keep your computer on
- **Automatic Posts**: 8 AM and 8 PM daily
- **Real Market Data**: Live stock prices and news
- **Free Tier**: Railway offers free hosting
- **Easy Management**: Update via GitHub, automatic deployments

## 🔧 Troubleshooting

### Check Logs
- Go to Railway dashboard → "Deployments" → Click latest deployment
- Check the logs for any errors

### Common Issues
1. **Missing Environment Variables**: Make sure all API keys are set
2. **API Rate Limits**: Free APIs have limits, bot will use sample data if needed
3. **X API Issues**: Check your X Developer Portal settings

### Restart Bot
- In Railway dashboard → "Deployments" → "Redeploy"

## 📊 Monitoring

The bot will:
- Log every hour: "Bot is running - [timestamp]"
- Log when posts are made: "Successfully posted to X"
- Log any errors for debugging

## 🎯 Success!

Once deployed, your bot will:
- ✅ Run 24/7 on Railway's servers
- ✅ Post market updates at 8 AM and 8 PM
- ✅ Use real market data when available
- ✅ Include news headlines for each stock
- ✅ Use randomized message formats

You can now turn off your Mac and the bot will keep running! 🚀 