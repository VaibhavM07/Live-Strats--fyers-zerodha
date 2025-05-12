import pandas as pd
import requests
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

class websocket():

    def __init__(self, client_id, secret_key, redirect_uri, response_type, grant_type, auth_code,token,expiry,strikes,symbols):
        self.client_id = client_id
        self.secret_key = secret_key
        self.redirect_uri = redirect_uri
        self.response_type = response_type
        self.grant_type = grant_type
        self.auth_code = auth_code
        self.token = token
        self.fyers = fyersModel.FyersModel(client_id=self.client_id, token=self.token, is_async=False,
                                           log_path="")
        self.expiry = expiry
        self.symbols = symbols
        self.strikes = strikes
        self.strike_list, self.pe_oi_list, self.ce_oi_list,self.Timestamp,self.ltp,self.volume = [],[],[],[],[],[]
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

    def onopen_ticks(self):
        data_type = "SymbolUpdate"
        symbols = self.symbols
        self.fyers_ticks.subscribe(symbols=symbols, data_type=data_type)
        self.fyers_ticks.keep_running()

    def onerror(self, message):
        print("Error:", message)

    def onclose(self, message):
        print("Connection closed:", message)

    def OI_data_set(self):


        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"

        # Headers to mimic a browser visit
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/"
        }

        # Make the HTTP request to the NSE API
        response = requests.get(url, headers=headers)

        # Initialize lists to store the parsed data

        if response.status_code == 200:
            data = response.json()  # Parse the JSON data from the response
            # Filter the required data for the specific expiry date
            records_data = data['records']['data']
            for i,record in enumerate(records_data):
                if record['expiryDate'] == self.expiry and record['strikePrice'] in self.strikes:
                    self.strike_list.append(self.symbols[i+1])
                    self.Timestamp.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    # Check if CE and PE data is available and multiply by lot size
                    if 'CE' in record:
                        self.ce_oi_list.append(record['CE']['openInterest'])  # Convert to millions
                    else:
                        self.ce_oi_list.append(0)
                    if 'PE' in record:
                        self.pe_oi_list.append(record['PE']['openInterest'])  # Convert to millions
                    else:
                        self.pe_oi_list.append(0)
        else:
            print("Failed to retrieve data:", response.status_code)

        self.df = pd.DataFrame({
                    "timestamp":self.Timestamp,
                    "Strike": self.strike_list,
                    "PE_OI": self.pe_oi_list,
                    "CE_OI": self.ce_oi_list
                    })
        print(self.df)
        return self.df
    def onmessage(self,message):
        t = time.localtime()
        #cmin = time.strftime("%M", t)
        csec = time.strftime("%S", t)
        #print(message)
        if int(csec) == 59:
            self.OI_data_set()
            time.sleep(1)
            for i in range(0,len(self.symbols)):
                if message['symbol']==self.symbols[i]:
                    self.strike_list.append(message['symbol']),
                    self.ltp.append(message['ltp']),
                    self.volume.append(message['vol_traded_today'])
                    self.df = pd.DataFrame({
                        "ltp": self.ltp,
                        "Symbols":self.strike_list,
                        "Volume":self.volume
                    })
                    print(self.df)

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

    #totp_key = 'NWCLJKF42ED5QKUXPCD4NQEHETJY6NCW'
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
        submit_button = WebDriverWait(driver, 10).until(
             EC.element_to_be_clickable((By.XPATH, '/html/body/section[8]/div[3]/div[3]/form/button'))
         )
        submit_button.click()

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
        client_id="CID",
        secret_key="SK",
        redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html",
        response_type="code",
        grant_type="authorization_code",
    )

    session.set_token(auth_code)

    response = session.generate_token()
    access_token = response['access_token']
    print(access_token)

    strike = [21250, 21300, 21350]
    obj = websocket(client_id="CI",
                         secret_key="SK",
                         redirect_uri="https://trade.fyers.in/api-login/redirect-uri/index.html",
                         response_type="code",
                         grant_type="authorization_code",
                         auth_code=auth_code,
                         token = access_token,
                        expiry="01-Feb-2024",
                        strikes= strike,
                        symbols= [#'NSE:NIFTY50-INDEX',
                                  'NSE:NIFTY24201'+str(strike[0])+'CE','NSE:NIFTY24201'+str(strike[1])+'CE',
                                  'NSE:NIFTY24201'+str(strike[2])+'CE','NSE:NIFTY24201'+str(strike[0])+'PE',
                                  'NSE:NIFTY24201'+str(strike[1])+'PE','NSE:NIFTY24201'+str(strike[2])+'PE',]
                         )
    obj.Fyers_ticks()
