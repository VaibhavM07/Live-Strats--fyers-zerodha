# -*- coding: utf-8 -*-
"""
Created on Tue Feb 28 01:07:07 2023

@author: vaibh
"""
import time
from kiteconnect import KiteConnect
from selenium import webdriver
import datetime as dt
import os
from pyotp import TOTP
import pandas as pd
from kiteconnect import KiteTicker
import numpy as np


cwd = os.chdir("C:\\Documents\\My Algo strategies\\Kite")

def autologin():
    token_path = "C:\\Documents\\My Algo strategies\\Kite\\api_key.txt"
    key_secret = open(token_path,'r').read().split()
    kite = KiteConnect(api_key=key_secret[0])
    service = webdriver.chrome.service.Service('./chromedriver')
    service.start()
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options = options.to_capabilities()
    driver = webdriver.Remote(service.service_url, options)
    driver.get(kite.login_url())
    driver.implicitly_wait(10)
    username = driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[1]/input')
    password = driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[2]/input')
    username.send_keys(key_secret[2])
    password.send_keys(key_secret[3])
    driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[4]/button').click()
    pin = driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[2]/div/input')
    totp = TOTP(key_secret[4])
    token = totp.now()
    pin.send_keys(token)
    driver.find_element_by_xpath('/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[3]/button').click()
    time.sleep(10)
    request_token=driver.current_url.split('request_token=')[1][:32]
    with open('request_token.txt', 'w') as the_file:
        the_file.write(request_token)
    driver.quit()

autologin()

#generating and storing access token - valid till 6 am the next day
request_token = open("request_token.txt",'r').read()
key_secret = open("api_key.txt",'r').read().split()
kite = KiteConnect(api_key=key_secret[0])
data = kite.generate_session(request_token, api_secret=key_secret[1])
with open('access_token.txt', 'w') as file:
        file.write(data["access_token"])


instrument_dump = kite.instruments("NSE")
instrument_df = pd.Dataframe(instrument_dump)

def instrument_lookup(instrument_df,symbol):
    try:
        return instrument_df[instrument_df.tradingsymbol == symbol].instrument_token.values[0]
    except:
        return -1
    
def fetchOHLC(ticker,interval,duration):
    instrument = instrument_lookup(instrument_df,ticker)
    data = kite.historical_data(instrument,dt.date.today()-dt.timedelta(duration), dt.date.today(),interval)
    data.set_index("date",inpalce = True)
    return data

OHLC = fetchOHLC("ACC","5minute",5) 

def placemarketorder(symbol,buy_sell,quantity):
    if buy_sell == "buy":
        t_type = kite.TRANSACTION_TYPE_BUY
    elif buy_sell == "sell":
        t_type = kite.TRANSACTION_TYPE_SELL

    kite.place_order(exchange = kite.EXCHANGE_NSE,tradingsymbol= symbol, transaction_type = t_type, quantity = quantity, 
                 product = kite.PRODUCT_MIS, 
                 order_type = kite.ORDER_TYPE_MARKET,
                 variety = kite.VARIETY_REGULAR)
    
placemarketorder("ACC","buy","10")

###################WEBSOCKET STREAMING-- TICK LEVEL DATA#################################################

def tokenlookup(instrument_df,symbol_list):
    token_list = []
    for symbol in symbol_list:
        token_list.append(int(instrument_df[instrument_df.tradingsymbol ==symbol].intrument_token.values[0]))
    return token_list

tickers = ["INFY","ACC","ICICIBANK"]

kws = KiteTicker(key_secret[0], kite.access_token)
tokens = tokenlookup(instrument_df, tickers)

def on_ticks(ws,ticks):
    print(ticks)

def on_connect(ws,response):
    # Callback on successful connect.
    # Subscribe to a list of instrument_tokens (RELIANCE and ACC here).
    #logging.debug("on connect: {}".format(response))
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL,tokens) # Set all token tick in `full` mode.
    #ws.set_mode(ws.MODE_LTP,[tokens[0]])  # Set one token tick in `full` mode.
 

kws.on_ticks=on_ticks
kws.on_connect=on_connect
kws.connect()

##################################TECHNICAL INDICATORS#######################################

def MACD(DF,a,b,c):
    """function to calculate MACD, here a,b,c are input for moving avgs"""
    df = DF.copy()
    df["MA_fast"] = df["close"].rolling(a).mean() #This is normal moving avg
    ## df["MA_fast"] = df["close"].ewm(span = a,min_periods = a).mean()----------- This is exponenetial moving avg
    
    df["MA_slow"] = df["close"].rolling(b).mean()
    df["MACD"] = df["MA_fast"]-df["MA_slow"]
    df["signal"] = df["MACD"].rolling(c).mean()
    df.dropna(inplace = True)
    return df
ohlc = fetchOHLC("ACC", "5minutes",5)
MACD(ohlc,12,26,9)

def Bollinger_bands(DF,n,s):
    #here s is the number of standard dev
    df = DF.copy()
    df["MA"] = df["close"].ewm(span=n,min_periods = n).mean()
    df["BB_up"] = df["MA"]+ s*df["close"].rolling(n).std(ddof=0)
    df["BB_down"] = df["MA"]- s*df["close"].rolling(n).std(ddof=0)
    df["BB_width"] = df["BB_up"]-df["BB_down"]
    df.dropna(inplace= True)
    return df

ohlc = fetchOHLC("ACC", "5minutes",5)
Bollinger_bands(ohlc,12,26,9)

def stocastic(DF):
    df =DF.copy()
    df['14-high'] = df['High'].rolling(14).max()
    df['14-low'] = df['Low'].rolling(14).min()
    df['%K'] = (df['Close'] - df['14-low'])*100/(df['14-high'] - df['14-low'])
    df['%D'] = df['%K'].rolling(3).mean()
    df['%K'] = df['%K'].apply(lambda a: round(a,2))
    df['%D'] = df['%D'].apply(lambda a: round(a,2))
    df.drop('14-low' , axis = 1 , inplace = True)
    df.drop('14-high' , axis = 1 , inplace = True)

ohlc = fetchOHLC("ACC", "5minutes",5)
stocastic(ohlc,12,26,9)

def fiveEMA(DF):
    df = DF.copy()
    df["5EMA"] = df["close"].ewm(span=5,min_periods=5).mean()
    df.dropna(inplace = True)
    return df
ohlc = fetchOHLC("ACC", "5minutes",5)
fiveEMA(ohlc,12,26,9)


def pivot(DF):
    df = DF.copy()
    df['PP'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['R1'] = 2 * df['PP'] - df['Low']
    df['S1'] = 2 * df['PP'] - df['High']
    df['R2'] = df['PP'] + (df['High'] - df['Low'])
    df['S2'] = df['PP'] - (df['High'] - df['Low'])
    df['R3'] = df['PP'] + 2 * (df['High'] - df['Low'])
    df['S3'] = df['PP'] - 2 * (df['High'] - df['Low'])
    return df
ohlc = fetchOHLC("ACC", "5minutes",5)
pivot(ohlc,12,26,9)


####******************** Pivot---- if candle<=15min: Previous day's OHLC.--- if 15min <= 1 hr - Previous week's OHLC,-- if 1hr<candle<=1 day - 1 month OHLC
        
def doji(DF):
    df = DF.copy()
    avg_doji = abs(df["close"]-df["open"]).median()
    df["doji"] = abs(df["close"]-df["open"]) <= (0.05* avg_doji)
    return df
ohlc = fetchOHLC("ACC", "5minutes",5)
doji(ohlc,12,26,9)

def hammer(ohlc_df):    
    """returns dataframe with hammer candle column"""
    df = ohlc_df.copy()
    df["hammer"] = (((df["high"] - df["low"])>3*(df["open"] - df["close"])) & \
                   ((df["close"] - df["low"])/(.001 + df["high"] - df["low"]) > 0.6) & \
                   ((df["open"] - df["low"])/(.001 + df["high"] - df["low"]) > 0.6)) & \
                   (abs(df["close"] - df["open"]) > 0.1* (df["high"] - df["low"]))
    return df
ohlc = fetchOHLC("ACC", "5minutes",5)
hammer(ohlc,12,26,9)

def shooting_star(ohlc_df):    
    """returns dataframe with shooting star candle column"""
    df = ohlc_df.copy()
    df["sstar"] = (((df["high"] - df["low"])>3*(df["open"] - df["close"])) & \
                   ((df["high"] - df["close"])/(.001 + df["high"] - df["low"]) > 0.6) & \
                   ((df["high"] - df["open"])/(.001 + df["high"] - df["low"]) > 0.6)) & \
                   (abs(df["close"] - df["open"]) > 0.1* (df["high"] - df["low"]))
    return df

ohlc = fetchOHLC("ACC", "5minutes",5)
shooting_star(ohlc,12,26,9)

def maru_bozu(ohlc_df):    
    """returns dataframe with maru bozu candle column"""
    df = ohlc_df.copy()
    avg_candle_size = abs(df["close"] - df["open"]).median()
    df["h-c"] = df["high"]-df["close"]
    df["l-o"] = df["low"]-df["open"]
    df["h-o"] = df["high"]-df["open"]
    df["l-c"] = df["low"]-df["close"]
    df["maru_bozu"] = np.where((df["close"] - df["open"] > 2*avg_candle_size) & \
                               (df[["h-c","l-o"]].max(axis=1) < 0.005*avg_candle_size),"maru_bozu_green",
                               np.where((df["open"] - df["close"] > 2*avg_candle_size) & \
                               (abs(df[["h-o","l-c"]]).max(axis=1) < 0.005*avg_candle_size),"maru_bozu_red",False))
    df.drop(["h-c","l-o","h-o","l-c"],axis=1,inplace=True)
    return df

ohlc = fetchOHLC("ASIANPAINT","5minute",30)
maru_bozu_df = maru_bozu(ohlc)

def trend(ohlc_df,n):# here n is the number of candles i want to capture
    "function to assess the trend by analyzing each candle"
    df = ohlc_df.copy()
    df["up"] = np.where(df["low"]>=df["low"].shift(1),1,0)## if True then 1 otherwise 0
    df["dn"] = np.where(df["high"]<=df["high"].shift(1),1,0)## if True then 1 otherwise 0
    if df["close"][-1] > df["open"][-1]:## if last candle is green that is last candle close is >> last candle open
        if df["up"][-1*n:].sum() >= 0.7*n:## iwant last 70% of the candles green
            return "uptrend"
    elif df["open"][-1] > df["close"][-1]:
        if df["dn"][-1*n:].sum() >= 0.7*n:
            return "downtrend"
    else:
        return None

ohlc = fetchOHLC("YESBANK","5minute",30)
trend(ohlc,8)      
   

