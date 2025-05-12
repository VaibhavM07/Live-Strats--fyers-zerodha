import time
from kiteconnect import KiteConnect
from selenium import webdriver
import datetime as dt
import os
#from pyotp import TOTP
import pandas as pd
from kiteconnect import KiteTicker
import numpy as np


cwd = os.chdir(".")

def login():
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
    username.send_keys("un")
    password.send_keys("pass")
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

login()

request_token = open("request_token.txt",'r').read()
api_key="i2b0tydpl9yi4kjp"
kite = KiteConnect(api_key)
data = kite.generate_session(request_token, api_secret="ymnf965hly3oorxql1lklj648beyrtnt")
access_token = data['access_token']
kite.set_access_token(access_token)
kws = KiteTicker(api_key, access_token)



instrument_dump = kite.instruments("NSE")
instrument_df = pd.DataFrame(instrument_dump)

for i in instrument_df["tradingsymbol"]:
    if "NIFTY" in i:
        print(i)

def instrumentLookup(instrument_df,symbol):

    try:
        return instrument_df[instrument_df.tradingsymbol==symbol].instrument_token.values[0]
    except:
        return -1


def fetchOHLC(ticker,interval,duration):

    instrumentt = instrumentLookup(instrument_df,ticker)
    data = pd.DataFrame(kite.historical_data(instrumentt,dt.date.today()-dt.timedelta(duration), dt.date.today(),interval))
    data.set_index("date",inplace=True)
    return data

def indicator(DF,n,s):
    #here s is the number of standard dev
    df = DF.copy()
    df["MA"] = df["close"].rolling(n).mean()
    df["BB_up"] = df["MA"]+ s*df["close"].rolling(n).std(ddof=0)
    df["BB_down"] = df["MA"]- s*df["close"].rolling(n).std(ddof=0)
    df["BB_width"] = df["BB_up"]-df["BB_down"]
    df.dropna(inplace= True)
    #signal only when K & D is above 80 or below 20 - buy when above 80 and K>D - opposite for sell
    df['14-high'] = df['high'].rolling(14).max()
    df['14-low'] = df['low'].rolling(14).min()
    df['%K'] = (df['close'] - df['14-low'])*100/(df['14-high'] - df['14-low'])
    df['%D'] = df['%K'].rolling(3).mean()

    df["5EMA"] = df["close"].ewm(span=5,min_periods=5).mean()
    df.dropna(inplace = True)
    return df


def condition(signal, DF):
    df = DF.copy()
    if (df["open"][-1])>=df["BB_up"][-2] and (df["low"][-1])>df["5EMA"][-1] and df["%K"][-1]>80 and df["%D"][-1]>80:
        signal.append("red")
    elif (df["open"][-1])<=df["BB_down"][-2] and (df["high"][-1])<df["5EMA"][-1] and df["%K"][-1]<20 and df["%D"][-1]<20:
        signal.append("green")
    return signal

# for i in range(3,len(ohlc1.index[100:191])):
#     condition(ohlc1.iloc[0:i])
#     if len(signal) > 0:
#         print(ohlc1.iloc[i])
#         signal.clear()

def put_condition(target_signal, DF, entry):
    df = DF.copy()
    if df['close'][-1] <= df["5EMA"][-1]:
        target_signal.append("squareoff_target_put")
    elif df["close"][-1] >= entry["high"]+(entry["high"]-entry["low"]):
        target_signal.append("squareoff_stoploss_put")
    return target_signal

def call_condition(target_signal, DF, entry):
    df = DF.copy()
    if df['close'][-1] >= df["5EMA"][-1]:
        target_signal.append("squareoff_target_call")
    elif df["close"][-1] <= entry["high"]+(entry["high"]-entry["low"]):
        target_signal.append("squareoff_stoploss_call")
    return target_signal


def weekly_expiry(kite):
    try :
        data = kite.instruments('NFO')
    except :
        time.sleep(5)
        data = kite.instruments('NFO')
    x = []
    for i in range(len(data)):
        x.append(data[i]['expiry'])

    x = list(set(x))
    x.sort()
    if dt.datetime.now().month <= x[0].month:
        expiry_date = x[0]

    if x[0].month == x[1].month:

        if x[0].month <= 3: # here 10 is october month
            expiry_date_month = str(x[0].month)
            return x[0].strftime('%y') + expiry_date_month + x[0].strftime('%d')
        else:
            expiry_date_month = ((dt.datetime.strptime(str(expiry_date.month), "%m")).strftime("%b"))[0]
            stringDate = str(expiry_date).split('-')
            formatedDate = f"{stringDate[0][2:]}{expiry_date_month.upper()}{stringDate[2]}"

    if x[0].month != x[1].month:
        expiry_date_month = ((dt.datetime.strptime(str(expiry_date.month), "%m")).strftime("%b"))
        stringDate = str(expiry_date).split('-')
        formatedDate = f"{stringDate[0][2:]}{expiry_date_month.upper()}"

    return formatedDate

def placeorder(kite, symbol, quantity, t_type):
    order= kite.place_order(variety = 'regular',
                         exchange = 'NFO',
                         tradingsymbol = symbol,
                         transaction_type = t_type,
                         quantity = quantity,
                         product='MIS',
                         order_type='MARKET',
                         validity='DAY')

def CancelOrder(order_id):
    # Modify order given order id
    kite.cancel_order(order_id=order_id,
                    variety=kite.VARIETY_REGULAR)


ohlc2 = []
entry = pd.DataFrame()
def main(ohlc2):
    entry = pd.DataFrame()
    TRADER_START_TIME = dt.time(hour=9, minute=20)
    TRADER_STOP_TIME = dt.time(hour=15, minute=30)

    if not dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME) > dt.datetime.today() > \
    dt.datetime.combine(dt.datetime.today(), TRADER_START_TIME):
        print('Sleeping till valid trade time')
        while not dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME) > dt.datetime.today() > \
        dt.datetime.combine(dt.datetime.today(), TRADER_START_TIME):
            time.sleep(1)
    print('Within valid trade time')

    exchange = 'NSE'
    instrument = 'NIFTY 50'
    bnf_symbol = exchange + ':' + instrument
    print('Banknifty index symbol:', bnf_symbol)
    strike = kite.ltp(bnf_symbol)[bnf_symbol]['last_price']
    strike = int(round(strike, -2))
    expiry = '23406'
    print(time.localtime())
    # At the money call and put options with latest weekly expiry dates
    bnf_ce_symbol = "NIFTY" + expiry + str(strike) + "CE"
    bnf_pe_symbol = "NIFTY" + expiry + str(strike) + "PE"
    print('Banknifty CE symbol:', bnf_ce_symbol)
    d = kite.positions()
    position = pd.DataFrame(d["day"])
    ord_df = pd.DataFrame(kite.orders())
    ohlc = fetchOHLC(instrument,"5minute",4)
    ohlc1 = indicator(ohlc,20,2)
    entry = ohlc.iloc[-4]
    print(ohlc1)
    print(position)
    while len(position.index) > 0 and ((len(position.loc[position['tradingsymbol'] == bnf_ce_symbol]['buy_quantity'].index) > 0 and position.loc[position['tradingsymbol'] == bnf_ce_symbol]['buy_quantity'].iloc[0] != position[position['tradingsymbol'] == bnf_ce_symbol]['sell_quantity'].iloc[0]) or (len(position.loc[position['tradingsymbol'] == bnf_pe_symbol]['buy_quantity'].index) > 0 and position.loc[position['tradingsymbol'] == bnf_pe_symbol]['buy_quantity'].iloc[0] != position[position['tradingsymbol'] == bnf_pe_symbol]['sell_quantity'].iloc[0])):
        d = kite.positions()
        print("jkd")
        position = pd.DataFrame(d["day"])
        target_signal = []
        target_signal = put_condition(target_signal, ohlc1, entry)
        print("jkd")
        if ohlc2[0] == "red" and len(target_signal) > 0 and target_signal[0] == "squareoff_target_put":
            placeorder(kite, bnf_pe_symbol, 50,"SELL")
        elif ohlc2[0] == "red" and len(target_signal) > 0 and target_signal[0] == "squareoff_stoploss_put":
            placeorder(kite, bnf_pe_symbol, 50,"SELL")
        print("jkd")
        target_signal = call_condition(target_signal, ohlc1, entry)
        if ohlc2[0] == "green" and len(target_signal) > 0 and target_signal[-1] == "squareoff_target_call":
            placeorder(kite, bnf_ce_symbol, 50,"SELL")
        elif ohlc2[0] == "green" and len(target_signal) > 0 and target_signal[-1] == "squareoff_stoploss_call":
            placeorder(kite, bnf_ce_symbol, 50,"SELL")
        time.sleep(120)

    entry.drop(entry.index, inplace=True)
    ohlc2.clear()
    ohlc2 = condition(ohlc2, ohlc1)
    #ohlc3 = target(ohlc1)
        #placing orders
    if len(ohlc2) > 0 and ohlc2[-1]=="red":
        placeorder(kite, bnf_pe_symbol, 50, "BUY")
        entry = ohlc1.iloc[-1]
    elif len(ohlc2) > 0 and ohlc2[-1]=="green":
        placeorder(kite, bnf_ce_symbol, 50, "BUY")
        entry = ohlc1.iloc[-1]

starttime=time.time()
timeout = time.time() + 60*60*5  # 60 seconds times 360 meaning 6 hrs
while time.time() <= timeout:
    try:
        main(ohlc2)
        time.sleep(300 - ((time.time() - starttime) % 300.0))
    except KeyboardInterrupt:
        print('\n\nKeyboard exception received. Exiting.')
        break
