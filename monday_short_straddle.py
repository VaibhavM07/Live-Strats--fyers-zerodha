import pandas as pd
from kiteconnect import KiteConnect, KiteTicker
import urllib.parse as urlparse
import onetimepass as otp
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime as dt
import os


def login():
        
    try:

        credentials = pd.read_excel('credentials.xlsx')
        name = str(credentials['Name'][0])
        user_id = str(credentials['User ID'][0])
        password = str(credentials['Password'][0])
        totp_key = str(credentials['PIN'][0])
        api_key = str(credentials['API Key'][0])
        api_secret = str(credentials['API Secret'][0])
        kite = KiteConnect(api_key=api_key)
        
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Chrome(options=options, executable_path=os.getcwd() + '/chromedriver')
        driver.get(kite.login_url())

        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))).send_keys(user_id)
        wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="password"]'))).send_keys(password)
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]'))).submit()
        time.sleep(5)
        
        totp = str(otp.get_totp(totp_key)).zfill(6)
        wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))).click()
        driver.find_element_by_xpath('//input[@type="text"]').send_keys(totp)
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]'))).submit()

        wait.until(EC.url_contains('status=success'))

        token_url = driver.current_url
        parsed = urlparse.urlparse(token_url)
        driver.close()
        request_token = urlparse.parse_qs(parsed.query)['request_token'][0]
        
        data = kite.generate_session(request_token, api_secret=api_secret)
        
        access_token = data['access_token']
        kite.set_access_token(access_token)
        kws = KiteTicker(api_key, access_token)
        
        print("Kite session generated successfully for {}".format(user_id))

        return kite, kws

    except Exception as e:
        print(e)
        raise


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
        if x[0].month < 10:
            expiry_date_month = str(x[0].month)
            return x[0].strftime('%y') + x[0].strftime('%#m') + x[0].strftime('%d')
        else:
            expiry_date_month = ((dt.datetime.strptime(str(expiry_date.month), "%m")).strftime("%b"))[0]
            stringDate = str(expiry_date).split('-')
            formatedDate = f"{stringDate[0][2:]}{expiry_date_month.upper()}{stringDate[2]}"

    if x[0].month != x[1].month:
        expiry_date_month = ((dt.datetime.strptime(str(expiry_date.month), "%m")).strftime("%b"))
        stringDate = str(expiry_date).split('-')
        formatedDate = f"{stringDate[0][2:]}{expiry_date_month.upper()}"

    return formatedDate


def short_market_order(kite, symbol, quantity):
    print(f'Placing market SELL order for {quantity} {symbol}')
    order_id = kite.place_order(variety = 'regular',
                         exchange = 'NFO',
                         tradingsymbol = symbol,
                         transaction_type = 'SELL',
                         quantity = quantity, 
                         product='MIS', 
                         order_type='MARKET',  
                         validity='DAY')     
    return order_id


def squareoff_market_order(kite, symbol, quantity):
    print(f'Placing market SELL order for {quantity} {symbol}')
    order_id = kite.place_order(variety = 'regular',
                         exchange = 'NFO',
                         tradingsymbol = symbol,
                         transaction_type = 'BUY',
                         quantity = quantity, 
                         product='MIS', 
                         order_type='MARKET',  
                         validity='DAY')     
    return order_id


def on_ticks(kws, ticks):
    for tick in ticks:
        ltp_dict[tick['instrument_token']] = float(tick['last_price'])


def on_connect(kws, response):
    print('Socket is opened')


def on_close(kws, code, reason):
    print("Socket is closed")


if __name__ == '__main__':

    TRADER_START_TIME = dt.time(hour=9, minute=29)
    TRADER_STOP_TIME = dt.time(hour=15, minute=15)

    if not dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME) > dt.datetime.today() > \
    dt.datetime.combine(dt.datetime.today(), TRADER_START_TIME):
        print('Sleeping till valid trade time')
        while not dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME) > dt.datetime.today() > \
        dt.datetime.combine(dt.datetime.today(), TRADER_START_TIME):
            time.sleep(1)
    print('Within valid trade time')

    print('Performing login')
    kite, kws = login()
    print('Login successful')

    exchange = 'NSE'
    instrument = 'NIFTY BANK'
    bnf_symbol = exchange + ':' + instrument
    print('Banknifty index symbol:', bnf_symbol)
    strike = kite.ltp(bnf_symbol)[bnf_symbol]['last_price']
    strike = int(round(strike, -2))
    expiry = weekly_expiry(kite)

    # At the money call and put options with latest weekly expiry dates
    bnf_ce_symbol = "BANKNIFTY" + expiry + str(strike) + "CE"
    bnf_pe_symbol = "BANKNIFTY" + expiry + str(strike) + "PE"

    # Subscribing to the instruments and monitoring their ltp to check combined stoploss exit
    bnf_ce_token =kite.ltp("NFO:"+bnf_ce_symbol)["NFO:"+bnf_ce_symbol]['instrument_token']
    bnf_pe_token =kite.ltp("NFO:"+bnf_pe_symbol)["NFO:"+bnf_pe_symbol]['instrument_token']
    token_list = [bnf_ce_token, bnf_pe_token]
    print('Banknifty call option (symbol, token): ({}, {})'.format(bnf_ce_symbol, bnf_ce_token))
    print('Banknifty put option (symbol, token): ({}, {})'.format(bnf_pe_symbol, bnf_pe_token))
    ltp_dict = dict()

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close
    kws.connect(threaded=True)
    time.sleep(5)

    kws.subscribe(token_list)
    kws.set_mode(kws.MODE_LTP, token_list)

    # Placing the orders
    ce_short_order_id = short_market_order(kite, bnf_ce_symbol, 25)
    pe_short_order_id = short_market_order(kite, bnf_pe_symbol, 25)
    time.sleep(5)
    print('Combined short straddle order placed')

    orders = kite.orders()
    ce_short_order = next(order for order in orders if order['order_id'] == ce_short_order_id)
    pe_short_order = next(order for order in orders if order['order_id'] == pe_short_order_id)

    while not (ce_short_order['status'] == 'COMPLETE' and pe_short_order['status'] == 'COMPLETE'):
        time.sleep(1)
    print('Combined short straddle order completed')

    combined_entry_price = ce_short_order['average_price'] + pe_short_order['average_price']
    combined_stoploss = combined_entry_price * 1.1
    print("Short straddle combined entry price:", combined_entry_price)
    print("Short straddle combined stoploss price:", combined_stoploss)

    stoploss_exit1 = 0

    while dt.datetime.today() < dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME):

        if ltp_dict[bnf_ce_token] + ltp_dict[bnf_pe_token] > combined_stoploss:
            print('Exiting short straddle position due to combined stoploss hit')
            ce_squareoff_order_id = squareoff_market_order(kite, bnf_ce_symbol, 25)
            pe_squareoff_order_id = squareoff_market_order(kite, bnf_pe_symbol, 25)
            if ltp_dict[bnf_ce_token] > ce_short_order['average_price']:
                leg = 'PE'
            elif ltp_dict[bnf_pe_token] > pe_short_order['average_price']:
                leg = 'CE'
            stoploss_exit1 = 1
            kws.unsubscribe(token_list)
            time.sleep(5)
            break
        else:
            time.sleep(1)

    if not stoploss_exit1:
        print("Exiting short straddle position due to trader's stop time exceeded")
        ce_squareoff_order_id = squareoff_market_order(kite, bnf_ce_symbol, 25)
        pe_squareoff_order_id = squareoff_market_order(kite, bnf_pe_symbol, 25)
        kws.unsubscribe(token_list)
        time.sleep(5)

    else:

        print('Entering a position in the 2nd leg: {}'.format(leg))
        strike = kite.ltp(bnf_symbol)[bnf_symbol]['last_price']
        strike = int(round(strike, -2))
        expiry = weekly_expiry(kite)
        bnf_leg_symbol = "BANKNIFTY" + expiry + str(strike) + leg

        bnf_leg_token =kite.ltp("NFO:"+bnf_leg_symbol)["NFO:"+bnf_leg_symbol]['instrument_token']
        print('Banknifty 2nd leg option (symbol, token): ({}, {})'.format(bnf_leg_symbol, bnf_leg_token))

        kws.subscribe([bnf_leg_token])
        kws.set_mode(kws.MODE_LTP, [bnf_leg_token])

        leg_short_order_id = short_market_order(kite, bnf_ce_symbol, 25)
        time.sleep(5)
        print('2nd leg short order placed')

        orders = kite.orders()
        leg_short_order = next(order for order in orders if order['order_id'] == leg_short_order_id)
        while not leg_short_order['status'] == 'COMPLETE':
            time.sleep(1)
        print('2nd leg short order completed')

        leg_entry_price = leg_short_order['average_price']
        leg_stoploss = leg_entry_price * 1.2
        stoploss_exit2 = 0
        print("2nd leg short entry price:", leg_entry_price)
        print("2nd leg stoploss price:", leg_stoploss)

        while dt.datetime.today() < dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME):

            if ltp_dict[bnf_leg_token] > leg_stoploss:
                print('Exiting 2nd leg short position due to stoploss hit')
                leg_squareoff_order_id = squareoff_market_order(kite, bnf_leg_symbol, 25)
                stoploss_exit2 = 1
                kws.unsubscribe([bnf_leg_token])
                time.sleep(5)
                break
            else:
                time.sleep(1)

        if not stoploss_exit2:
            print("Exiting 2nd leg short position due to trader's stop time exceeded")
            leg_squareoff_order_id = squareoff_market_order(kite, bnf_leg_symbol, 25)
            kws.unsubscribe([bnf_leg_token])
            time.sleep(5)