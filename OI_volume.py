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


def oi_data():
    data = {
        "symbol": "NSE:SBIN-EQ",
        "ohlcv_flag": "0",
        "oi_flag":1
    }
    response1 = fyers.depth(data=data)
    print(response1)

def data_set():
    yesterday = datetime.today() - timedelta(days=1)
    yesterday = yesterday.strftime('%yyyy-%mm-%dd')
    required_data = {
        "symbol": "NSE:RCOM-EQ",
        "resolution": "1",
        "date_format": "1",
        "range_from":yesterday,
        "range_to":datetime.today().strftime('%yyyy-%mm-%dd'),
        "cont_flag": "0"
    }
    response2 = fyers.history(data=required_data)
    data = pd.DataFrame.from_dict(response2["candles"])
    columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    data.columns = columns
    data['datetime'] = pd.to_datetime(data['datetime'], unit="s")
    data['datetime'] = data['datetime'].dt.tz_localize('utc').dt.tz_convert('Asia/Kolkata')
    data['datetime'] = data['datetime'].dt.tz_localize(None)
    data = data.set_index('datetime')
    return data


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

    totp_key = '2QOCFE7DZHRCDKWKZ4L7YKBEUXOYEOES'
    otp = pyotp.TOTP(totp_key)

    redirect_url = url
    driver = webdriver.Edge()
    driver.get(redirect_url)
    print('Page loaded successfully!!')

    try:
        # Click the login link
        login_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[1]/div[3]/div[3]/form/a'))
        )
        login_link.click()

        # Input Client ID
        client_id_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[2]/div[3]/div[3]/form/div[1]/input'))
        )
        client_id_input.send_keys(id)

        # Click Client ID button
        client_id_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/section[2]/div[3]/div[3]/form/button'))
        )
        client_id_button.click()

        # Input OTP
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

        # Input password
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

    # Set the authorization code in the session object
    session.set_token(auth_code)

    # Generate the access token using the authorization code
    response = session.generate_token()
    access_token = response['access_token']

    client_id = "9MKDYQFWFB-100"
    token =access_token
    fyers = fyersModel.FyersModel(client_id=client_id, token=token, is_async=False,
                                  log_path="")
    oi_data()