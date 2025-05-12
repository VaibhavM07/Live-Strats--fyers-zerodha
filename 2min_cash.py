from fyers_apiv3.FyersWebsocket import order_ws
from fyers_apiv3.FyersWebsocket import data_ws
from datetime import datetime, timedelta, timezone
import pandas as pd
from fyers_apiv3 import fyersModel
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyotp
import time
import hashlib


class websocket():

    def __init__(self, client_id, secret_key, redirect_uri, response_type, grant_type, auth_code, token):
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.response_type = response_type
        self.grant_type = grant_type
        self.auth_code = auth_code
        self.token = token
        self.fyers = fyersModel.FyersModel(client_id=self.client_id, token=self.token, is_async=False,
                                           log_path="")

    def Fyers_ticks(self):
        self.fyers_ticks = data_ws.FyersDataSocket(
            access_token=self.token,
            log_path="",
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_connect=self.onopen_ticks,
            on_close=self.onclose,
            on_error=self.onerror,
            on_message=self.onmessage
        )
        self.fyers_ticks.connect()
        print(self.fyers_ticks)
        print("wesocket data:")

    def Fyers_position_orders(self):
        self.fyers_po = order_ws.FyersOrderSocket(
            access_token=self.auth_code,
            write_to_file=False,
            log_path="",
            on_connect=self.onopen_position_orders,
            on_close=self.onclose,
            on_error=self.onerror,
            on_orders=self.onOrder,
        )
        self.fyers_po.connect()

    def data_set(self):
        yesterday = datetime.today() - timedelta(days=1)
        yesterday = yesterday.strftime('%y-%m-%d')
        required_data = {
            "symbol": "NSE:NIFTYBANK-INDEX",
            "resolution": "2",
            "date_format": "1",
            "range_from": datetime.today().strftime('%y-%m-%d'),
            "range_to": datetime.today().strftime('%y-%m-%d'),
            "cont_flag": "0"
        }
        response = self.fyers.history(data=required_data)
        data = pd.DataFrame.from_dict(response["candles"])
        columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        data.columns = columns
        data['datetime'] = pd.to_datetime(data['datetime'], unit="s")
        data['datetime'] = data['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
        data['datetime'] = data['datetime'].dt.tz_localize(None)
        data = data.set_index('datetime')
        data["ema"] = data["close"].ewm(span=5, min_periods=5).mean()
        data['14-high'] = data['high'].rolling(14).max()
        data['14-low'] = data['low'].rolling(14).min()
        data['%K'] = (data['close'] - data['14-low']) * 100 / (data['14-high'] - data['14-low'])
        data['%D'] = data['%K'].rolling(3).mean()
        self.emadata = data
        print(self.emadata)

    def onmessage(self, message):
        return message

    def onerror(self, message):
        print("Error:", message)

    def onclose(self, message):
        print("Connection closed:", message)

    def onopen_ticks(self):
        data_type = "SymbolUpdate"
        symbols = ['NSE:NIFTYBANK-INDEX']
        self.fyers_ticks.subscribe(symbols=symbols, data_type=data_type)
        self.fyers_ticks.keep_running()

    def onopen_position_orders(self):
        data_type = "OnPositions,OnOrders"

        symbols = ['NSE:360ONE-EQ', 'NSE:APLAPOLLO-EQ', 'NSE:AUBANK-EQ', 'NSE:AARTIDRUGS-EQ', 'NSE:AARTIIND-EQ',
                   'NSE:AAVAS-EQ', 'NSE:ADANIPOWER-EQ', 'NSE:ABCAPITAL-EQ']

        self.fyers_ticks.subscribe(symbols=symbols, data_type=data_type)

        self.fyers_ticks.keep_running()

    def onPosition(self, message):
        # print("Position Response:", message)
        return message

    def onOrder(self, message):
        print("Order Response:", message)

    def backtest(self):

        df = pd.DataFrame(columns=['short', 'long', 'sl', 'tgt'])
        t = time.localtime()
        cmin = time.strftime("%M", t)
        csec = time.strftime("%S", t)
        pos = None
        stoploss = None
        target = None

        if (int(cmin) % 5 == 0 and int(csec) < 3):
            print("5 ema data updated")
            self.data_set()
            time.sleep(1)
        symb = "NSE:NIFTYBANK-INDEX"
        ema = self.emadata['ema'].iloc[-2]
        l = self.emadata['low'].iloc[-2]
        print(f"{self.emadata['close']} | low {l} |ema {ema} | ")
        for i in range(1, len(self.emadata)):
            print(self.emadata['high'].iloc[i], self.emadata['ema'].iloc[i - 1], "next", self.emadata['open'].iloc[i],
                  self.emadata['ema'].iloc[i - 1], "next ", self.emadata['low'].iloc[i],
                  self.emadata['ema'].iloc[i - 1], "next ",
                  self.emadata['low'][i], self.emadata['low'].iloc[i - 1])
            ##   Short condition  ###
            if (self.emadata['close'].iloc[i - 1] > self.emadata['ema'].iloc[i - 1]
                    and self.emadata['high'].iloc[i - 1] > self.emadata['ema'].iloc[i - 1]
                    and self.emadata['open'].iloc[i - 1] > self.emadata['ema'].iloc[i - 1]
                    and (self.emadata['low'].iloc[i - 1] - self.emadata['ema'].iloc[i - 1]) >= 10
                    and self.emadata['low'][i] < self.emadata['low'].iloc[i - 1]
                    and self.emadata["%K"][i - 1] > 95 and self.emadata["%D"][i - 1] > 95
            ):
                sp = int(round(self.emadata['low'][i], -2))
                strike = "NSE:BANKNIFTY24110" + str(sp) + "PE"
                print(f"entry {strike}")
                pos = 1
                print("#### SHORT #####")
                df.loc[i, 'short'] = 1
                df.loc[i, 'long'] = 0
                stoploss = (self.emadata['high'].iloc[i - 1]) + 30
                # 1:2 Risk Reward
                target = self.emadata['close'][i - 1] - (
                        (self.emadata['high'].iloc[i - 1] - self.emadata['low'].iloc[i - 1]) * 2)
            if (pos == 1 and self.emadata['close'][i + 1] >= stoploss):
                print("stop loss")
                df.loc[i, 'sl'] = 1
                df.loc[i, 'tgt'] = 0
                pos = 0
                stoploss = 0
                target = 0

            if (pos == 1 and self.emadata['close'][i + 1] <= target):

                print("traget ")
                df.loc[i, 'tgt'] = 1
                df.loc[i, 'sl'] = 0

                pos = 0
                stoploss = 0
                target = 0
                print(f"symbol {symb} and ltp {self.emadata['close']} | low {l} |ema {ema} | ")
                print(f"success {self.emadata['close']}")

            ## Long condition

            elif (self.emadata['close'].iloc[i - 1] < self.emadata['ema'].iloc[i - 1]
                  and self.emadata['low'].iloc[i - 1] < self.emadata['ema'].iloc[i - 1]
                  and self.emadata['open'].iloc[i - 1] < self.emadata['ema'].iloc[i - 1]
                  and (self.emadata['ema'].iloc[i - 1] - self.emadata['high'].iloc[i - 1]) >= 10
                  and self.emadata['high'][i] > self.emadata['high'].iloc[i - 1]
                  and self.emadata["%K"][i - 1] < 10 and self.emadata["%D"][i - 1] < 10
            ):

                sp = int(round(self.emadata['high'][i], -2))
                strike = "NSE:BANKNIFTY24110" + str(sp) + "CE"

                print(f"entry {strike}")
                pos = 1
                df.loc[i, 'long'] = 1
                df.loc[i, 'short'] = 0
                print("#### LONG #######")
                stoploss = (self.emadata['high'].iloc[i - 1]) - 30
                # 1:3 Risk Reward
                target = self.emadata['close'][i - 1] - (
                        (self.emadata['high'].iloc[i - 1] - self.emadata['low'].iloc[i - 1]) * 2)
            if (pos == 1 and self.emadata['close'][i + 1] <= stoploss):
                print("stop loss")
                df.loc[i, 'sl'] = 1
                df.loc[i, 'tgt'] = 0
                pos = 0
                stoploss = 0
                target = 0
                time.sleep(1)
            if (pos == 1 and self.emadata['close'][i + 1] >= target):
                print("traget ")
                df.loc[i, 'tgt'] = 1
                df.loc[i, 'sl'] = 0
                pos = 0
                stoploss = 0
                target = 0
                time.sleep(1)
        short_pos = (df['short'] == 1).sum()
        long_pos = (df['long'] == 1).sum()
        number_of_stoplosses = (df['sl'] == 1).sum()
        number_of_target_hit = (df['tgt'] == 1).sum()
        hit_ratio = (number_of_target_hit / (number_of_stoplosses + number_of_target_hit)) * 100
        print("short_pos: ", short_pos, ",", " long_pos: ", long_pos, ",", " number_of_stoplosses: ",
              number_of_stoplosses, ",", " number_of_target_hit: ", number_of_target_hit, ",", " hit_ratio: ",
              hit_ratio, "%")

        return df


if __name__ == "__main__":
    appsession = fyersModel.SessionModel(
        client_id="9MKDYQFWFB-100",
        secret_key="SJI15AAODY",
        redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html",
        response_type='code',
        state='sample_state',
        grant_type='authorization_code'
    )

    url = appsession.generate_authcode()
    print(url)

    id = 'FK0247'
    p1 = '1'
    p2 = '2'
    p3 = '3'
    p4 = '4'

    # totp_key = 'NWCLJKF42ED5QKUXPCD4NQEHETJY6NCW'
    totp_key = "2QOCFE7DZHRCDKWKZ4L7YKBEUXOYEOES"
    otp = pyotp.TOTP(totp_key)

    redirect_url = url
    driver = webdriver.Edge()
    driver.get(redirect_url)
    print('Page loaded successfully!!')

    try:
        login_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[1]/div[3]/div[3]/form/a'))
        )
        login_link.click()

        client_id_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[2]/div[3]/div[3]/form/div[1]/input'))
        )
        client_id_input.send_keys(id)

        client_id_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[2]/div[3]/div[3]/form/button'))
        )
        client_id_button.click()

        otp_inputs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '/html/body/section[6]/div[3]/div[3]/form/div[3]/input'))
        )
        otp_digits = str(otp.now())
        for i, digit in enumerate(otp_digits, ):
            digit_input = driver.find_element(By.XPATH,
                                              f'/html/body/section[6]/div[3]/div[3]/form/div[3]/input[{i + 1}]')
            driver.execute_script("arguments[0].scrollIntoView(true);", digit_input)
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
                (By.XPATH, f'/html/body/section[6]/div[3]/div[3]/form/div[3]/input[{i + 1}]')))
            digit_input.send_keys(digit)
        otp_click = driver.find_element(by='xpath',
                                        value='/html/body/section[6]/div[3]/div[3]/form/button').click()

        password_inputs = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, '/html/body/section[8]/div[3]/div[3]/form/div[2]/input'))
        )
        pin_input = driver.find_element(By.XPATH, '//html/body/section[8]/div[3]/div[3]/form/div[2]/input')
        driver.execute_script("arguments[0].scrollIntoView(true);", pin_input)
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[8]/div[3]/div[3]/form/div[2]/input')))
        password_inputs[0].send_keys(p1)
        password_inputs[1].send_keys(p2)
        password_inputs[2].send_keys(p3)
        password_inputs[3].send_keys(p4)

        # Click the submit button
        # submit_button = WebDriverWait(driver, 10).until(
        #     EC.element_to_be_clickable((By.XPATH, '/html/body/section[8]/div[3]/div[3]/form/button'))
        # )
        # submit_button.click()

        # Get the access token
        access_token_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, '/html/body/main/section/div/div/div[2]/div/div/table/tbody/tr[3]/td/p'))
        )
        auth_code = access_token_element.text
        print("Access Token:", auth_code)

    except ElementNotInteractableException as e:
        print("Element is not interactable:", e)


    finally:
        driver.quit()

    #
    # def generate_sha256(input_string):
    #     sha256_hash = hashlib.sha256(input_string.encode()).hexdigest()
    #     return sha256_hash
    #
    # appIdHash = generate_sha256(auth_code)
    # appIdHash = appIdHash+'KMSCOJRAFH'

    session = fyersModel.SessionModel(
        client_id="9MKDYQFWFB-100",
        secret_key="SJI15AAODY",
        redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html",
        response_type="code",
        grant_type="authorization_code",
    )

    session.set_token(auth_code)

    response = session.generate_token()
    access_token = response['access_token']
    print(access_token)

    obj = websocket(client_id="9MKDYQFWFB-100",
                    secret_key="SJI15AAODY",
                    redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html",
                    response_type="code",
                    grant_type="authorization_code",
                    auth_code=auth_code,
                    token=access_token
                    )

    obj.data_set()
    df = obj.backtest()
    print(df)


