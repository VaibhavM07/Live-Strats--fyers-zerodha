import time
from kiteconnect import KiteConnect
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import datetime as dt
import os
import pyotp
import pandas as pd
from kiteconnect import KiteTicker
import numpy as np
import pandas as pd
from fyers_apiv3 import fyersModel
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyotp



cwd = os.chdir(".")
today = dt.now().date().strftime('%Y-%m-%d')
totp_key = "LAVSB735BO3DWXBYMJW6OZPKRHXOC4V3"
def login():
    kite = KiteConnect(api_key="98gwz42tqv6nle3g")
    service = webdriver.edge.service.Service('./msedgedriver')
    service.start()
    options = webdriver.EdgeOptions()
    #options.add_argument('--headless')
    driver = webdriver.Edge(options=options)
    driver.get(kite.login_url())
    driver.implicitly_wait(10)
    username = driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[1]/input')
    password = driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[2]/input')
    username.send_keys("")
    password.send_keys("")
    driver.find_element('xpath','/html/body/div[1]/div/div[2]/div[1]/div/div/div[2]/form/div[4]/button').click()
    time.sleep(1)
    pin_el = driver.find_element(
        'xpath', '/html/body/div[1]/div/div[2]/div[1]/div[2]/div/div[2]/form/div[1]/input')
    authkey = pyotp.TOTP(totp_key)
    pin_el.send_keys(authkey.now())
    time.sleep(1)
    print(driver.current_url)
    request_token=driver.current_url.split('request_token=')[1][:32]
    with open('request_token.txt', 'w') as the_file:
        the_file.write(request_token)
    driver.quit()

login()

request_token = open("request_token.txt",'r').read()
api_key="98gwz42tqv6nle3g"
kite = KiteConnect(api_key)
data = kite.generate_session(request_token, api_secret="atng6jgmon2pb6ajopisee2gn9dn0c51")
access_token = data['access_token']
kite.set_access_token(access_token)
kws = KiteTicker(api_key, access_token)



instrument_dump = kite.instruments("NSE")
instrument_df = pd.DataFrame(instrument_dump)

def instrumentLookup(instrument_df,symbol):

    try:
        return instrument_df[instrument_df.tradingsymbol==symbol].instrument_token.values[0]
    except:
        return -1


def fetchOHLC(ticker,interval,from_date):

    instrument = instrumentLookup(instrument_df,ticker)
    data = pd.DataFrame(kite.historical_data(instrument,from_date,to_date= today, interval=interval))
    data.set_index("date",inplace=True)
    return data


def entry_logic(DF,ticker):
    df = DF.copy()
    if kite.ltp(ticker)[ticker]["last_price"]>df["high"][-1]:
        entry_price = kite.ltp(ticker)
        long = 1
    return entry_price, long


def stoploss_logic(DF,ticker):
    df = DF.copy()
    if kite.ltp(ticker)[ticker]["last_price"] <= df["low"][-1]:
        stoploss = 1
        exit_stoploss_price = kite.ltp(ticker)

    return stoploss, exit_stoploss_price

def target_logic(DF,ticker):
    exit_half = 0
    df = DF.copy()
    if kite.ltp(ticker)[ticker]["last_price"] >= (df["high"][-1]-df["low"][-1]):
        exit_half = 1
        exit_price = kite.ltp(ticker)[ticker]["last_price"]
    elif exit_half == 1 and ((kite.ltp(ticker)[ticker]["last_price"] >= (3 * (df["high"][-1] - df["low"][-1]))) or (
                    dt.now().time().hour == 15 and dt.now().time().minute == 15)):
        exit_full = 1
        exit_price_full = kite.ltp(ticker)
    return exit_price, exit_price_full, exit_half, exit_full

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


def main():
    TRADER_START_TIME = dt.time(hour=9, minute=15)
    TRADER_STOP_TIME = dt.time(hour=15, minute=30)

    if not dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME) > dt.datetime.today() > \
    dt.datetime.combine(dt.datetime.today(), TRADER_START_TIME):
        print('Sleeping till valid trade time')
        while not dt.datetime.combine(dt.datetime.today(), TRADER_STOP_TIME) > dt.datetime.today() > \
        dt.datetime.combine(dt.datetime.today(), TRADER_START_TIME):
            time.sleep(1)
    print('Within valid trade time')
    tickers = ['NSE:360ONE',
'NSE:APLAPOLLO',
'NSE:AUBANK',
'NSE:AARTIDRUGS',
'NSE:AARTIIND',
'NSE:AAVAS',
'NSE:ADANIPOWER',
'NSE:ABCAPITAL',
'NSE:ABFRL',
'NSE:AEGISCHEM',
'NSE:AETHER',
'NSE:AFFLE',
'NSE:AJANTPHARM',
'NSE:APLLTD',
'NSE:AMARAJABAT',
'NSE:ANGELONE',
'NSE:ANURAS',
'NSE:APOLLOTYRE',
'NSE:APTUS',
'NSE:ACI',
'NSE:ASAHIINDIA',
'NSE:ASHOKLEY',
'NSE:ASTERDM',
'NSE:AUROPHARMA',
'NSE:AVANTIFEED',
'NSE:BLS',
'NSE:BSE',
'NSE:BALRAMCHIN',
'NSE:BANDHANBNK',
'NSE:BANKINDIA',
'NSE:MAHABANK',
'NSE:BATAINDIA',
'NSE:BDL',
'NSE:BHARATFORG',
'NSE:BHEL',
'NSE:BIKAJI',
'NSE:BIOCON',
'NSE:BIRLACORPN',
'NSE:BSOFT',
'NSE:BLUESTARCO',
'NSE:BBTC',
'NSE:BORORENEW',
'NSE:BRIGADE',
'NSE:BCG',
'NSE:MAPMYINDIA',
'NSE:CCL',
'NSE:CESC',
'NSE:CGPOWER',
'NSE:CIEINDIA',
'NSE:CSBBANK',
'NSE:CAMPUS',
'NSE:CANFINHOME',
'NSE:CGCL',
'NSE:CARBORUNIV',
'NSE:CASTROLIND',
'NSE:CENTRALBK',
'NSE:CDSL',
'NSE:CENTURYPLY',
'NSE:CENTURYTEX',
'NSE:CHALET',
'NSE:CHAMBLFERT',
'NSE:CHEMPLASTS',
'NSE:CHOLAHLDNG',
'NSE:CUB',
'NSE:CLEAN',
'NSE:COCHINSHIP',
'NSE:CONCOR',
'NSE:COROMANDEL',
'NSE:CREDITACC',
'NSE:CROMPTON',
'NSE:CUMMINSIND',
'NSE:CYIENT',
'NSE:DCMSHRIRAM',
'NSE:DALBHARAT',
'NSE:DEEPAKFERT',
'NSE:DEEPAKNTR',
'NSE:DELHIVERY',
'NSE:DELTACORP',
'NSE:DEVYANI',
'NSE:EIDPARRY',
'NSE:EIHOTEL',
'NSE:EPL',
'NSE:EASEMYTRIP',
'NSE:ELGIEQUIP',
'NSE:EMAMILTD',
'NSE:ENDURANCE',
'NSE:ENGINERSIN',
'NSE:EQUITASBNK',
'NSE:ERIS',
'NSE:EXIDEIND',
'NSE:FDC',
'NSE:FEDERALBNK',
'NSE:FACT',
'NSE:FINCABLES',
'NSE:FINPIPE',
'NSE:FSL',
'NSE:FIVESTAR',
'NSE:FORTIS',
'NSE:GRINFRA',
'NSE:GMMPFAUDLR',
'NSE:GMRINFRA',
'NSE:GICRE',
'NSE:GLAND',
'NSE:GLAXO',
'NSE:GLENMARK',
'NSE:MEDANTA',
'NSE:GOCOLORS',
'NSE:GODREJAGRO',
'NSE:GODREJIND',
'NSE:GODREJPROP',
'NSE:GRANULES',
'NSE:GRAPHITE',
'NSE:GESHIP',
'NSE:GREENPANEL',
'NSE:GUJALKALI',
'NSE:GAEL',
'NSE:GUJGASLTD',
'NSE:GNFC',
'NSE:GPPL',
'NSE:GSFC',
'NSE:GSPL',
'NSE:HEG',
'NSE:HFCL',
'NSE:HAPPSTMNDS',
'NSE:HIKAL',
'NSE:HGS',
'NSE:HINDCOPPER',
'NSE:HINDPETRO',
'NSE:HINDZINC',
'NSE:HOMEFIRST',
'NSE:HUDCO',
'NSE:ISEC',
'NSE:IDBI',
'NSE:IDFCFIRSTB',
'NSE:IDFC',
'NSE:IFBIND',
'NSE:IIFL',
'NSE:IRB',
'NSE:ITI',
'NSE:INDIACEM',
'NSE:IBULHSGFIN',
'NSE:IBREALEST',
'NSE:INDIANB',
'NSE:IEX',
'NSE:INDHOTEL',
'NSE:IOB',
'NSE:IRFC',
'NSE:INDIGOPNTS',
'NSE:IGL',
'NSE:INFIBEAM',
'NSE:INTELLECT',
'NSE:IPCALAB',
'NSE:JBMA',
'NSE:JKLAKSHMI',
'NSE:JKPAPER',
'NSE:JMFINANCIL',
'NSE:JSWENERGY',
'NSE:JAMNAAUTO',
'NSE:JSL',
'NSE:JINDWORLD',
'NSE:JUBLFOOD',
'NSE:JUBLINGREA',
'NSE:JUBLPHARMA',
'NSE:JUSTDIAL',
'NSE:JYOTHYLAB',
'NSE:KPRMILL',
'NSE:KNRCON',
'NSE:KPITTECH',
'NSE:KRBL',
'NSE:KAJARIACER',
'NSE:KPIL',
'NSE:KALYANKJIL',
'NSE:KANSAINER',
'NSE:KARURVYSYA',
'NSE:KEC',
'NSE:RUSTOMJEE',
'NSE:KFINTECH',
'NSE:KIMS',
'NSE:L&TFH',
'NSE:LICHSGFIN',
'NSE:LATENTVIEW',
'NSE:LAURUSLABS',
'NSE:LXCHEM',
'NSE:LEMONTREE',
'NSE:LUPIN',
'NSE:LUXIND',
'NSE:MMTC',
'NSE:LODHA',
'NSE:MGL',
'NSE:M&MFIN',
'NSE:MHRIL',
'NSE:MAHLIFE',
'NSE:MAHLOG',
'NSE:MANAPPURAM',
'NSE:MRPL',
'NSE:MANKIND',
'NSE:MFSL',
'NSE:MAXHEALTH',
'NSE:MAZDOCK',
'NSE:MEDPLUS',
'NSE:MFL',
'NSE:METROBRAND',
'NSE:METROPOLIS',
'NSE:MSUMI',
'NSE:MOTILALOFS',
'NSE:MCX',
'NSE:NATCOPHARM',
'NSE:NBCC',
'NSE:NCC',
'NSE:NHPC',
'NSE:NLCINDIA',
'NSE:NMDC',
'NSE:NSLNISP',
'NSE:NOCIL',
'NSE:NH',
'NSE:NATIONALUM',
'NSE:NAZARA',
'NSE:NETWORK18',
'NSE:NAM-INDIA',
'NSE:NUVOCO',
'NSE:OBEROIRLTY',
'NSE:OIL',
'NSE:OLECTRA',
'NSE:PAYTM',
'NSE:ORIENTELEC',
'NSE:POLICYBZR',
'NSE:PCBL',
'NSE:PNBHOUSING',
'NSE:PNCINFRA',
'NSE:PVRINOX',
'NSE:PATANJALI',
'NSE:PETRONET',
'NSE:PHOENIXLTD',
'NSE:PEL',
'NSE:PPLPHARMA',
'NSE:POLYMED',
'NSE:POLYPLEX',
'NSE:POONAWALLA',
'NSE:PFC',
'NSE:PRAJIND',
'NSE:PRESTIGE',
'NSE:PRINCEPIPE',
'NSE:PRSMJOHNSN',
'NSE:PNB',
'NSE:QUESS',
'NSE:RBLBANK',
'NSE:RECLTD',
'NSE:RHIM',
'NSE:RITES',
'NSE:RADICO',
'NSE:RVNL',
'NSE:RAIN',
'NSE:RAINBOW',
'NSE:RAJESHEXPO',
'NSE:RALLIS',
'NSE:RCF',
'NSE:RTNINDIA',
'NSE:RAYMOND',
'NSE:REDINGTON',
'NSE:RELAXO',
'NSE:RBA',
'NSE:ROSSARI',
'NSE:ROUTE',
'NSE:SJVN',
'NSE:SAPPHIRE',
'NSE:SHARDACROP',
'NSE:SHOPERSTOP',
'NSE:RENUKA',
'NSE:SHRIRAMFIN',
'NSE:SHYAMMETL',
'NSE:SOBHA',
'NSE:SONACOMS',
'NSE:SONATSOFTW',
'NSE:STARHEALTH',
'NSE:SAIL',
'NSE:SWSOLAR',
'NSE:STLTECH',
'NSE:SUMICHEM',
'NSE:SPARC',
'NSE:SUNTV',
'NSE:SUNDRMFAST',
'NSE:SUNTECK',
'NSE:SUPRAJIT',
'NSE:SUVENPHAR',
'NSE:SUZLON',
'NSE:SWANENERGY',
'NSE:SYNGENE',
'NSE:TCIEXP',
'NSE:TCNSBRANDS',
'NSE:TTKPRESTIG',
'NSE:TV18BRDCST',
'NSE:TVSMOTOR',
'NSE:TMB',
'NSE:TANLA',
'NSE:TATACHEM',
'NSE:TATACOMM',
'NSE:TTML',
'NSE:TEJASNET',
'NSE:NIACL',
'NSE:RAMCOCEM',
'NSE:TORNTPOWER',
'NSE:TCI',
'NSE:TRIDENT',
'NSE:TRIVENI',
'NSE:TRITURBINE',
'NSE:UCOBANK',
'NSE:UFLEX',
'NSE:UNOMINDA',
'NSE:UTIAMC',
'NSE:UNIONBANK',
'NSE:UBL',
'NSE:VGUARD',
'NSE:VIPIND',
'NSE:VAIBHAVGBL',
'NSE:VTL',
'NSE:VARROC',
'NSE:MANYAVAR',
'NSE:VIJAYA',
'NSE:VINATIORGA',
'NSE:IDEA',
'NSE:VOLTAS',
'NSE:WELCORP',
'NSE:WELSPUNIND',
'NSE:WESTLIFE',
'NSE:WHIRLPOOL',
'NSE:YESBANK',
'NSE:ZEEL',
'NSE:ZENSARTECH',
'NSE:ZYDUSLIFE',
'NSE:ZYDUSWELL',
'NSE:ECLERX',
]

    for ticker in tickers:
        ohlc = fetchOHLC(ticker, "5minute", f'{today} 09:15:00')