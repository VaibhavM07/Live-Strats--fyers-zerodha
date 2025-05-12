# -*- coding: utf-8 -*-
"""
Created on Sun Mar  5 02:17:21 2023

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


cwd = os.chdir(".")

def autologin():
    kite = KiteConnect(api_key="i2b0tydpl9yi4kjp")
    service = webdriver.chrome.service.Service('./chromedriver')
    service.start()
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    driver.get(kite.login_url())
    driver.implicitly_wait(10)
    username = driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[1]/input')
    password = driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[2]/input')
    username.send_keys("SN")
    password.send_keys("PS")
    driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[4]/button').click()
    # pin_el = driver.find_element('xpath','//*[@id="container"]/div/div/div[2]/form/div[2]/input')
    # pin = str(input())
    # print(pin)
    # pin_el.send_keys(pin)
    # driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[3]/button').click()
    time.sleep(10)
    print(driver.current_url)
    request_token=driver.current_url.split('request_token=')[1][:32]
    with open('request_token.txt', 'w') as the_file:
        the_file.write(request_token)
    driver.quit()

autologin()


request_token = open("request_token.txt",'r').read()
kite = KiteConnect(api_key="i2b0tydpl9yi4kjp")
data = kite.generate_session(request_token, api_secret="ymnf965hly3oorxql1lklj648beyrtnt")
with open('access_token.txt', 'w') as file:
        file.write(data["access_token"])


instrument_dump = kite.instruments("NSE")
instrument_df = pd.DataFrame(instrument_dump)


def instrumentLookup(instrument_df,symbol):

    try:
        return instrument_df[instrument_df.tradingsymbol==symbol].instrument_token.values[0]
    except:
        return -1


def fetchOHLC(ticker,interval,duration):

    instrument = instrumentLookup(instrument_df,ticker)
    data = pd.DataFrame(kite.historical_data(instrument,dt.date.today()-dt.timedelta(duration), dt.date.today(),interval))
    data.set_index("date",inplace=True)
    return data


def atr(DF,n):

    df = DF.copy()
    df['H-L']=abs(df['high']-df['low'])
    df['H-PC']=abs(df['high']-df['close'].shift(1))
    df['L-PC']=abs(df['low']-df['close'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    df['ATR'] = df['TR'].ewm(com=n,min_periods=n).mean()
    return df['ATR']


def Supertrend(df, atr_period, multiplier):

    high = df['high']
    low = df['low']
    close = df['close']

    # calculate ATR
    price_diffs = [high - low,
                   high - close.shift(),
                   close.shift() - low]
    true_range = pd.concat(price_diffs, axis=1)
    true_range = true_range.abs().max(axis=1)
    # default ATR calculation in supertrend indicator
    atr = true_range.ewm(alpha=1/atr_period,min_periods=atr_period).mean()
    # df['atr'] = df['tr'].rolling(atr_period).mean()

    # HL2 is simply the average of high and low prices
    hl2 = (high + low) / 2
    # upperband and lowerband calculation
    # notice that final bands are set to be equal to the respective bands
    final_upperband = upperband = hl2 + (multiplier * atr)
    final_lowerband = lowerband = hl2 - (multiplier * atr)

    # initialize Supertrend column to True
    supertrend = [True] * len(df)

    for i in range(1, len(df.index)):
        curr, prev = i, i-1

        # if current close price crosses above upperband
        if close[curr] > final_upperband[prev]:
            supertrend[curr] = True
        # if current close price crosses below lowerband
        elif close[curr] < final_lowerband[prev]:
            supertrend[curr] = False
        # else, the trend continues
        else:
            supertrend[curr] = supertrend[prev]

            # adjustment to the final bands
            if supertrend[curr] == True and final_lowerband[curr] < final_lowerband[prev]:
                final_lowerband[curr] = final_lowerband[prev]
            if supertrend[curr] == False and final_upperband[curr] > final_upperband[prev]:
                final_upperband[curr] = final_upperband[prev]

        # to remove bands according to the trend direction
        if supertrend[curr] == True:
            final_upperband[curr] = np.nan
        else:
            final_lowerband[curr] = np.nan

    return pd.DataFrame({
        'Supertrend'+str(atr_period): supertrend,
        'Final Lowerband'+str(atr_period): final_lowerband,
        'Final Upperband'+str(atr_period): final_upperband
    }, index=df.index)

def st_dir_refresh(super_trend,ticker,i):
    """To check for supertrend reversal"""
    if super_trend[-1]:
        st_dir[ticker][i] = "green"
    else:
        st_dir[ticker][i] = "red"

def sl_price(ohlc):
    """To calculate stop loss based on supertrends"""
    st = ohlc.loc[-1,['Supertrend7', 'Supertrend10', 'Supertrend11']]
    if st.min() > ohlc["close"][-1]:
        sl = (0.6*st.sort_values(ascending = True)[0]) + (0.4*st.sort_values(ascending = True)[1])
    elif st.max() < ohlc["close"][-1]:
        sl = (0.6*st.sort_values(ascending = False)[0]) + (0.4*st.sort_values(ascending = False)[1])
    else:
        sl = st.mean()
    return round(sl,1)

def placeSLOrder(symbol,buy_sell,quantity,sl_price):

    if buy_sell == "buy":
        t_type=kite.TRANSACTION_TYPE_BUY
        t_type_sl=kite.TRANSACTION_TYPE_SELL
    elif buy_sell == "sell":
        t_type=kite.TRANSACTION_TYPE_SELL
        t_type_sl=kite.TRANSACTION_TYPE_BUY
    kite.place_order(tradingsymbol=symbol,
                    exchange=kite.EXCHANGE_NSE,
                    transaction_type=t_type,
                    quantity=quantity,
                    order_type=kite.ORDER_TYPE_MARKET,
                    product=kite.PRODUCT_MIS,
                    variety=kite.VARIETY_REGULAR)
    kite.place_order(tradingsymbol=symbol,
                    exchange=kite.EXCHANGE_NSE,
                    transaction_type=t_type_sl,
                    quantity=quantity,
                    order_type=kite.ORDER_TYPE_SL,
                    price=sl_price,
                    trigger_price = sl_price,
                    product=kite.PRODUCT_MIS,
                    variety=kite.VARIETY_REGULAR)


def ModifyOrder(order_id,price):

    kite.modify_order(order_id=order_id,
                    price=price,
                    trigger_price=price,
                    order_type=kite.ORDER_TYPE_SL,
                    variety=kite.VARIETY_REGULAR)

def main(capital):
    a,b = 0,0
    while a < 10:
        try:
            pos_df = pd.DataFrame(kite.positions()["day"])
            break
        except:
            print("can't extract position data..retrying")
            a+=1
    while b < 10:
        try:
            ord_df = pd.DataFrame(kite.orders())
            break
        except:
            print("can't extract order data..retrying")
            b+=1

    for ticker in tickers:
        print("starting passthrough for.....",ticker)
        try:
            ohlc = fetchOHLC(ticker,"5minute",4)
            supertrend = Supertrend(ohlc, 7, 3)
            ohlc = ohlc.join(supertrend)
            supertrend = Supertrend(ohlc, 10, 4)
            ohlc = ohlc.join(supertrend)
            supertrend = Supertrend(ohlc, 11, 3)
            ohlc = ohlc.join(supertrend)

            st_dir_refresh(list(ohlc['Supertrend7']), ticker, 0)
            st_dir_refresh(list(ohlc['Supertrend10']), ticker, 1)
            st_dir_refresh(list(ohlc['Supertrend11']), ticker, 2)
            quantity = int(capital/ohlc["close"][-1])
            if len(pos_df.columns)==0:
                if st_dir[ticker] == ["green","green","green"]:
                    placeSLOrder(ticker,"buy",quantity,sl_price(ohlc))
                if st_dir[ticker] == ["red","red","red"]:
                    placeSLOrder(ticker,"sell",quantity,sl_price(ohlc))
            if len(pos_df.columns)!=0 and ticker not in pos_df["tradingsymbol"].tolist():
                if st_dir[ticker] == ["green","green","green"]:
                    placeSLOrder(ticker,"buy",quantity,sl_price(ohlc))
                if st_dir[ticker] == ["red","red","red"]:
                    placeSLOrder(ticker,"sell",quantity,sl_price(ohlc))
            if len(pos_df.columns)!=0 and ticker in pos_df["tradingsymbol"].tolist():
                if pos_df[pos_df["tradingsymbol"]==ticker]["quantity"].values[0] == 0:
                    if st_dir[ticker] == ["green","green","green"]:
                        placeSLOrder(ticker,"buy",quantity,sl_price(ohlc))
                    if st_dir[ticker] == ["red","red","red"]:
                        placeSLOrder(ticker,"sell",quantity,sl_price(ohlc))
                if pos_df[pos_df["tradingsymbol"]==ticker]["quantity"].values[0] != 0:
                    order_id = ord_df.loc[(ord_df['tradingsymbol'] == ticker) & (ord_df['status'].isin(["TRIGGER PENDING","OPEN"]))]["order_id"].values[0]
                    ModifyOrder(order_id,sl_price(ohlc))
        except Exception as e:
            print("API error for ticker :",ticker)
            print(str(e))

#############################################################################################################
#############################################################################################################
tickers = ["HDFC","SBIN","ICICIBANK", "TCS", "INFY", "HCLTECH", "RELIANCE", "ITC", "WIPRO", "HDFCBANK", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "BAJAJFINSV", "MARUTI", "ULTRACEMCO", "TATAMOTORS", "HINDUNILVR", "ASIANPAINT", "NESTLEIND", "BRITANNIA", "HEROMOTOCO", "BAJAJ-AUTO", "GRASIM", "SHREECEM", "TECHM", "TATASTEEL", "DRREDDY", "CIPLA", "COALINDIA", "POWERGRID", "BHARTIARTL", "EICHERMOT", "HINDALCO", "IOC", "JSWSTEEL", "LT", "M&M", "NTPC", "ONGC", "SBILIFE", "TATAMTRDVR", "TATAPOWER", "UPL", "VEDL", "ADANIPORTS", "INDUSINDBK", "ZEEL", "GAIL", "INDIGO", "MOTHERSUMI", "MUTHOOTFIN", "NATIONALUM", "PNB", "TITAN", "WOCKPHARMA", "YESBANK", "AMBUJACEM", "APOLLOTYRE", "AUROPHARMA", "BANDHANBNK", "BATAINDIA", "BERGEPAINT", "CADILAHC", "CANBK", "CASTROLIND", "CENTURYTEX", "CHOLAFIN", "COLPAL", "CONCOR", "CUMMINSIND", "DABUR", "DIVISLAB", "DLF", "GODREJCP", "GODREJIND", "GODREJPROP", "GRANULES", "HAVELLS"]

capital = 10000 #position size
st_dir = {} #directory to store super trend status for each ticker
for ticker in tickers:
    st_dir[ticker] = ["None","None","None"]

# ohlc = fetchOHLC(tickers[0],"5minute",4)
# ohlc["st1"] = supertrend(ohlc,7,3)
# ohlc["st2"] = supertrend(ohlc,10,3)
# ohlc["st3"] = supertrend(ohlc,11,2)

# print(ticker, " ", ohlc)
# st_dir_refresh(ohlc,ticker)
# st_dir

# pos_df = pd.DataFrame(kite.positions()["day"])
# if len(pos_df.columns)==0:
#     if st_dir[ticker] == ["green","green","green"]:
#         placeSLOrder(ticker,"buy",quantity,sl_price(ohlc))
#     if st_dir[ticker] == ["red","red","red"]:
#         placeSLOrder(ticker,"sell",quantity,sl_price(ohlc))

starttime=time.time()
timeout = time.time() + 60*60*4  # 60 seconds times 360 meaning 6 hrs
while time.time() <= timeout:
    try:
        main(capital)
        time.sleep(300 - ((time.time() - starttime) % 300.0))
    except KeyboardInterrupt:
        print('\n\nKeyboard exception received. Exiting.')
        break

def placeMarketOrder(symbol,buy_sell,quantity):
    # Place an intraday market order on NSE
    if buy_sell == "buy":
        t_type=kite.TRANSACTION_TYPE_BUY
    elif buy_sell == "sell":
        t_type=kite.TRANSACTION_TYPE_SELL
    kite.place_order(tradingsymbol=symbol,
                    exchange=kite.EXCHANGE_NSE,
                    transaction_type=t_type,
                    quantity=quantity,
                    order_type=kite.ORDER_TYPE_MARKET,
                    product=kite.PRODUCT_MIS,
                    variety=kite.VARIETY_REGULAR)

def CancelOrder(order_id):
    # Modify order given order id
    kite.cancel_order(order_id=order_id,
                    variety=kite.VARIETY_REGULAR)

#fetching orders and position information
a,b = 0,0
while a < 10:
    try:
        pos_df = pd.DataFrame(kite.positions()["day"])
        break
    except:
        print("can't extract position data..retrying")
        a+=1
while b < 10:
    try:
        ord_df = pd.DataFrame(kite.orders())
        break
    except:
        print("can't extract order data..retrying")
        b+=1

#closing all open position
for i in range(len(pos_df)):
    ticker = pos_df["tradingsymbol"].values[i]
    if pos_df["quantity"].values[i] >0:
        quantity = pos_df["quantity"].values[i]
        placeMarketOrder(ticker,"sell", quantity)
    if pos_df["quantity"].values[i] <0:
        quantity = abs(pos_df["quantity"].values[i])
        placeMarketOrder(ticker,"buy", quantity)

#closing all pending orders
pending = ord_df[ord_df['status'].isin(["TRIGGER PENDING","OPEN"])]["order_id"].tolist()
drop = []
attempt = 0
while len(pending)>0 and attempt<5:
    pending = [j for j in pending if j not in drop]
    for order in pending:
        try:
            CancelOrder(order)
            drop.append(order)
        except:
            print("unable to delete order id : ",order)
            attempt+=1
