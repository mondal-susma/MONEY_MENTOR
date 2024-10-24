import csv
import json
import random
import requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Portfolio, StockHolding
from riskprofile.models import RiskProfile
from riskprofile.views import risk_profile

from django.shortcuts import render
from nbconvert import HTMLExporter
import nbformat

# AlphaVantage API
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
import subprocess as sp

# def get_alphavantage_key():
#   alphavantage_keys = [
#     settings.ALPHAVANTAGE_KEY1,
#     settings.ALPHAVANTAGE_KEY2,
#     settings.ALPHAVANTAGE_KEY3,
#     settings.ALPHAVANTAGE_KEY4,
#     settings.ALPHAVANTAGE_KEY5,
#     settings.ALPHAVANTAGE_KEY6,
#     settings.ALPHAVANTAGE_KEY7,
#   ]

#   for key in alphavantage_keys:
#         if not key:
#             print(f"Error: Missing API key in settings.")
#             return None  # Or handle the error appropriately
  
#   selected_key = random.choice(alphavantage_keys)
#   print(f"Selected AlphaVantage API Key: {selected_key}")  # This will print the selected key
#   return selected_key
#   # return random.choice(alphavantage_keys)

# Global variable to track the current key index
current_key_index = 0

def get_alphavantage_key():
    global current_key_index

    alphavantage_keys = [
        settings.ALPHAVANTAGE_KEY1,
        settings.ALPHAVANTAGE_KEY2,
        settings.ALPHAVANTAGE_KEY3,
        settings.ALPHAVANTAGE_KEY4,
        settings.ALPHAVANTAGE_KEY5,
        settings.ALPHAVANTAGE_KEY6,
        settings.ALPHAVANTAGE_KEY7,
    ]

    # Ensure all keys are present
    for key in alphavantage_keys:
        if not key:
            print(f"Error: Missing API key in settings.")
            return None  # Or handle the error appropriately

    # Select the next key in the list
    selected_key = alphavantage_keys[current_key_index]
    print(f"Selected AlphaVantage API Key: {selected_key}")  # This will print the selected key

    # Rotate to the next key
    current_key_index = (current_key_index + 1) % len(alphavantage_keys)

    return selected_key

def handle_api_request():
    global current_key_index

    while True:
        try:
            api_key = get_alphavantage_key()
            if api_key is None:
                return HttpResponse("API key error")

            # Call the Alpha Vantage API with the selected key
            response = make_api_call(api_key)

            # Check if the response is valid, else raise an exception
            if "Missing price data" in response:
                raise ValueError("Missing price data")

            return response

        except ValueError as e:
            print(f"Error occurred: {e}")
            current_key_index = (current_key_index + 1) % len(settings.ALPHAVANTAGE_KEYS)
            continue
        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            return HttpResponse("Unexpected error occurred")



@login_required
def dashboard(request):
  if RiskProfile.objects.filter(user=request.user).exists():
    try:
      portfolio = Portfolio.objects.get(user=request.user)
    except:
      portfolio = Portfolio.objects.create(user=request.user)
    portfolio.update_investment()
    holding_companies = StockHolding.objects.filter(portfolio=portfolio)
    holdings = []
    sectors = [[], []]
    sector_wise_investment = {}
    stocks = [[], []]
    for c in holding_companies:
      company_symbol = c.company_symbol
      company_name = c.company_name
      number_shares = c.number_of_shares
      investment_amount = c.investment_amount
      average_cost = investment_amount / number_shares
      holdings.append({
        'CompanySymbol': company_symbol,
        'CompanyName': company_name,
        'NumberShares': number_shares,
        'InvestmentAmount': investment_amount,
        'AverageCost': average_cost,
        'LTP': random.randint(50, 150),
        'PNL': random.randint(50, 150),
        'Net': random.randint(50, 150)
      })
      stocks[0].append(round((investment_amount / portfolio.total_investment) * 100, 2))
      stocks[1].append(company_symbol)
      if c.sector in sector_wise_investment:
        sector_wise_investment[c.sector] += investment_amount
      else:
        sector_wise_investment[c.sector] = investment_amount
    for sec in sector_wise_investment.keys():
      sectors[0].append(round((sector_wise_investment[sec] / portfolio.total_investment) * 100, 2))
      sectors[1].append(sec)

    # Adding
    news = fetch_news()
    ###

    context = {
      'holdings': holdings,
      'totalInvestment': portfolio.total_investment,
      'stocks': stocks,
      'sectors': sectors,
      'news': news,
      'currentValue': 520
    }

    return render(request, 'dashboard/dashboard.html', context)
  else:
    return redirect(risk_profile)


def get_portfolio_insights(request):
  try:
    portfolio = Portfolio.objects.get(user=request.user)
    holding_companies = StockHolding.objects.filter(portfolio=portfolio)
    fd = FundamentalData(key=get_alphavantage_key(), output_format='json')
    portfolio_beta = 0
    portfolio_pe = 0
    for c in holding_companies:
      data, meta_data = fd.get_company_overview(symbol=c.company_symbol)
      portfolio_beta += float(data['Beta']) * (c.investment_amount / portfolio.total_investment)
      portfolio_pe += float(data['PERatio']) * (c.investment_amount / portfolio.total_investment)
    return JsonResponse({"PortfolioBeta": portfolio_beta, "PortfolioPE": portfolio_pe})
  except Exception as e:
    return JsonResponse({"Error": str(e)})


def update_values(request):
  try:
    portfolio = Portfolio.objects.get(user=request.user)
    current_value = 0
    unrealized_pnl = 0
    growth = 0
    holding_companies = StockHolding.objects.filter(portfolio=portfolio)
    stockdata = {}
    for c in holding_companies:
      ts = TimeSeries(key=get_alphavantage_key(), output_format='json')
      data, meta_data = ts.get_quote_endpoint(symbol=c.company_symbol)
      last_trading_price = float(data['05. price'])
      pnl = (last_trading_price * c.number_of_shares) - c.investment_amount
      net_change = pnl / c.investment_amount
      stockdata[c.company_symbol] = {
        'LastTradingPrice': last_trading_price,
        'PNL': pnl,
        'NetChange': net_change * 100
      }
      current_value += (last_trading_price * c.number_of_shares)
      unrealized_pnl += pnl
    growth = unrealized_pnl / portfolio.total_investment
    return JsonResponse({
      "StockData": stockdata, 
      "CurrentValue": current_value,
      "UnrealizedPNL": unrealized_pnl,
      "Growth": growth * 100
    })
  except Exception as e:
    return JsonResponse({"Error": str(e)})


def get_financials(request):
  try:
    fd = FundamentalData(key=get_alphavantage_key(), output_format='json')
    data, meta_data = fd.get_company_overview(symbol=request.GET.get('symbol'))
    financials = {
      "52WeekHigh": data['52WeekHigh'],
      "52WeekLow": data['52WeekLow'],
      "Beta": data['Beta'],
      "BookValue": data['BookValue'],
      "EBITDA": data['EBITDA'],
      "EVToEBITDA": data['EVToEBITDA'],
      "OperatingMarginTTM": data['OperatingMarginTTM'],
      "PERatio": data['PERatio'],
      "PriceToBookRatio": data['PriceToBookRatio'],
      "ProfitMargin": data['ProfitMargin'],
      "ReturnOnAssetsTTM": data['ReturnOnAssetsTTM'],
      "ReturnOnEquityTTM": data['ReturnOnEquityTTM'],
      "Sector": data['Sector'],
    }
    return JsonResponse({ "financials": financials })
  except Exception as e:
    return JsonResponse({"Error": str(e)})


# def add_holding(request):
#   if request.method == "POST":
#     try:
#       portfolio = Portfolio.objects.get(user=request.user)
#       holding_companies = StockHolding.objects.filter(portfolio=portfolio)
#       company_symbol = request.POST['company'].split('(')[1].split(')')[0]
#       company_name = request.POST['company'].split('(')[0].strip()
#       number_stocks = int(request.POST['number-stocks'])
#       ts = TimeSeries(key=get_alphavantage_key(), output_format='json')
#       data, meta_data = ts.get_daily(symbol=company_symbol, outputsize='full')
#       buy_price = float(data[request.POST['date']]['4. close'])
#       fd = FundamentalData(key=get_alphavantage_key(), output_format='json')
#       data, meta_data = fd.get_company_overview(symbol=company_symbol)
#       sector = data['Sector']

#       found = False
#       for c in holding_companies:
#         if c.company_symbol == company_symbol:
#           c.buying_value.append([buy_price, number_stocks])
#           c.save()
#           found = True

#       if not found:
#         c = StockHolding.objects.create(
#           portfolio=portfolio, 
#           company_name=company_name, 
#           company_symbol=company_symbol,
#           number_of_shares=number_stocks,
#           sector=sector
#         )
#         c.buying_value.append([buy_price, number_stocks])
#         c.save()

#       return HttpResponse("Success")
#     except Exception as e:
#       print(e)
#       return HttpResponse(e)

def add_holding(request):
    if request.method == "POST":
        try:
            portfolio = Portfolio.objects.get(user=request.user)
            holding_companies = StockHolding.objects.filter(portfolio=portfolio)
            
            company_data = request.POST.get('company', '').strip()
            number_stocks = int(request.POST.get('number-stocks', 0))
            company_symbol = company_data.split('(')[1].split(')')[0] if '(' in company_data and ')' in company_data else ''
            company_name = company_data.split('(')[0].strip() if '(' in company_data and ')' in company_data else ''
            
            # if not company_symbol or not company_name:
            #     return HttpResponse("Invalid company data format")

            # ts = TimeSeries(key=get_alphavantage_key(), output_format='json')
            # data, meta_data = ts.get_daily(symbol=company_symbol, outputsize='full')
            
            # if '4. close' not in data.get(request.POST.get('date', ''), {}):
            #     return HttpResponse("Missing price data")

            # buy_price = float(data[request.POST['date']]['4. close'])
            
            # fd = FundamentalData(key=get_alphavantage_key(), output_format='json')
            # data, meta_data = fd.get_company_overview(symbol=company_symbol)
            
            # sector = data.get('Sector', 'Unknown')
            
            buy_price = 250
            sector = "Financial"

            found = False
            for c in holding_companies:
                if c.company_symbol == company_symbol:
                    c.buying_value.append([buy_price, number_stocks])
                    c.save()
                    found = True
                    break

            if not found:
                c = StockHolding.objects.create(
                    portfolio=portfolio, 
                    company_name=company_name, 
                    company_symbol=company_symbol,
                    number_of_shares=number_stocks,
                    sector=sector
                )
                c.buying_value.append([buy_price, number_stocks])
                c.save()

            return HttpResponse("Success")
        
        except Exception as e:
            # Log the exception for debugging
            print(f"An error occurred: {e}")
            return HttpResponse(f"An error occurred: {e}")

    return HttpResponse("Invalid request method")

def send_company_list(request):
  with open('nasdaq-listed.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    rows = []
    for row in csv_reader:
      if line_count == 0:
        line_count += 1
      else:
        rows.append([row[0], row[1]])
        line_count += 1
  return JsonResponse({"data": rows})


def fetch_news():
  query_params = {
    "country": "us",
    "category": "business",
    "sortBy": "top",
    "apiKey": settings.NEWSAPI_KEY
  }
  main_url = "https://newsapi.org/v2/top-headlines"
  # fetching data in json format
  res = requests.get(main_url, params=query_params)
  open_bbc_page = res.json()
  # getting all articles in a string article
  article = open_bbc_page["articles"]
  results = []
  for ar in article:
    results.append([ar["title"], ar["description"], ar["url"]])
  # Make news as 2 at a time to show on dashboard
  news = zip(results[::2], results[1::2])
  if len(results) % 2:
    news.append((results[-1], None))
  return news


def backtesting(request):
  print('Function Called')
  try:
    output = sp.check_output("quantdom", shell=True)
  except sp.CalledProcessError:
    output = 'No such command'
  return HttpResponse("Success")

def view_notebook(request):
    # Path to your .ipynb file
    notebook_path = r"C:\Users\swamy\Downloads\Portfolio-Management-System-main\Portfolio-Management-System-main\portfolio_management_system\stock.ipynb"

    # Read the notebook file
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_content = f.read()

    # Parse the notebook content
    notebook = nbformat.reads(notebook_content, as_version=4)

    # Convert notebook to HTML
    html_exporter = HTMLExporter()
    (body, resources) = html_exporter.from_notebook_node(notebook)

    # Render the HTML content in your template
    return render(request, 'dashboard/view_notebook.html', {'notebook_html': body})