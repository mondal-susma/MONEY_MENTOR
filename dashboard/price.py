import requests
from django.shortcuts import render

def get_stock_data(symbol):
    api_key = 'YOUR_ALPHA_VANTAGE_API_KEY'
    base_url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': api_key
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    return float(data['Global Quote']['05. price'])

def get_usd_to_inr():
    api_key = 'YOUR_ALPHA_VANTAGE_API_KEY'
    base_url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'CURRENCY_EXCHANGE_RATE',
        'from_currency': 'USD',
        'to_currency': 'INR',
        'apikey': api_key
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    return float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])

def dashboard(request):
    symbols = ['RELIANCE.NS', 'HDFCBANK.NS', 'INFY.NS', 'TCS.NS', 'ICICIBANK.NS']
    usd_to_inr = get_usd_to_inr()
    stock_data = {symbol: get_stock_data(symbol) * usd_to_inr for symbol in symbols}
    
    context = {
        'stock_data': stock_data,
        'usd_to_inr': usd_to_inr,
    }
    
    return render(request, 'dashboard/dashboard.html', context)
