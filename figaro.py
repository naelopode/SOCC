import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import html_to_json
from selenium import webdriver
import pandas as pd
import dateparser
import os 
from bs4 import BeautifulSoup
import http.cookiejar


PWD = os.path.abspath(os.getcwd())
URL = "https://recherche.lefigaro.fr/recherche/"
URL_LOGIN = "https://lefigaro.fr/"

#Thanks to https://stackoverflow.com/questions/41721734/take-screenshot-of-full-page-with-selenium-python-with-chromedriver
def save_screenshot(driver: webdriver.Chrome, path: str = '/mnt/2To/jupyter_data/socc/screenie.png') -> None:
    original_size = driver.get_window_size()
    required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
    required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
    driver.set_window_size(required_width, required_height)
    driver.find_element(By.XPATH,'/html/body').screenshot(path)  # avoids scrollbar
    driver.set_window_size(original_size['width'], original_size['height'])

def convert_date_to_french(date_str):
    # Dictionary to map month numbers to French month names
    months = {
        '01': 'janvier', '02': 'février', '03': 'mars', '04': 'avril',
        '05': 'mai', '06': 'juin', '07': 'juillet', '08': 'août',
        '09': 'septembre', '10': 'octobre', '11': 'novembre', '12': 'décembre'
    }

    # Splitting the date string
    day, month, year = date_str.split('/')

    # Removing leading zero from day and converting year to full year
    day = str(int(day))  # Converts '01' to '1'

    # Formatting the date in French
    french_date = f"{day} {months[month]} {year}"

    return french_date

def parse_netscape_cookie_file(cookie_file):
    cj = http.cookiejar.MozillaCookieJar(cookie_file)
    cj.load()
    return cj

def add_cookies_to_driver(driver, cookie_jar):
    for cookie in cookie_jar:
        cookie_dict = {
            'name': cookie.name,
            'value': cookie.value,
            'path': cookie.path,
            'domain': cookie.domain
        }
        if cookie.expires:
            cookie_dict['expiry'] = cookie.expires
        if cookie.secure:
            cookie_dict['secure'] = cookie.secure
        driver.add_cookie(cookie_dict)

def scroll(driver):
    SCROLL_PAUSE_TIME = 0.5

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    return

def fetch_figaro(SEARCH, DATE_FROM, DATE_TO, DEBUG=False):
    DATE_FROM=convert_date_to_french(DATE_FROM)
    DATE_TO=convert_date_to_french(DATE_TO)
    try:
        print('setting options') if DEBUG else None
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--no-sandbox')
        print('opening driver') if DEBUG else None
        driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=options)
        print('getting page') if DEBUG else None
        width = 1920 # in pixels
        height = 1080 # in pixels
        driver.set_window_size(width, height)
        driver.get(URL)

        print('page loaded') if DEBUG else None
        print('saving screenshot pre cookie') if DEBUG else None
        driver.implicitly_wait(10)  # Wait for 10 seconds
        print('waiting for frame') if DEBUG else None
        save_screenshot(driver, os.path.join(PWD,'screen_step0.png')) if DEBUG else None
        try:
            print('accepting cookies') if DEBUG else None
            driver.switch_to.frame(driver.find_element(By.XPATH,'//iframe[@title="Consent window"]'))
            driver.find_element(By.XPATH,"/html/body/div/div/div/div/div/div/div[4]/div/button[1]").click()
        except:
            print("Cookies already accepted") if DEBUG else None

        print('saving screenshot post cookie') if DEBUG else None
        save_screenshot(driver, os.path.join(PWD,'screen_step1.png')) if DEBUG else None


        ## Search
        driver.find_element(By.XPATH, '//*[@id="recherche-input"]').send_keys(SEARCH)

        ### Submit
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[1]/form/button').click()
        save_screenshot(driver, os.path.join(PWD,'screen_step2.png')) if DEBUG else None

        ### Date
        print('setting date') if DEBUG else None

        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div/div[2]/ul/li[8]/label').click()
        save_screenshot(driver, os.path.join(PWD,'screen_step3.png')) if DEBUG else None

        print('setting date') if DEBUG else None
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div/div[2]/ul/li[8]/ul[2]/li/form/span[1]/input[2]').send_keys(DATE_FROM)
        save_screenshot(driver, os.path.join(PWD,'screen_step4.png')) if DEBUG else None

        print('setting date2') if DEBUG else None
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div/div[2]/ul/li[8]/ul[2]/li/form/span[2]/input[2]').send_keys(DATE_TO)
        ### Submit
        driver.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div[2]/div/div[2]/ul/li[8]/ul[2]/li/form/input').click()
        
        time.sleep(1)
        print('saving screenshot end search') if DEBUG else None
        save_screenshot(driver, os.path.join(PWD,'screen_step5.png')) if DEBUG else None

        print('checking number of pages') if DEBUG else None
        try:
            print(driver.find_element(By.XPATH, "/html/body/div[2]/div/div[2]/div[1]/button").text) if DEBUG else None
            driver.find_element(By.XPATH, "/html/body/div[2]/div/div[2]/div[1]/button").click()
            print('attempting to scroll') if DEBUG else None
            scroll(driver)
        except:
            print("no more search") if DEBUG else None
        print('fetching articles') if DEBUG else None
        time.sleep(1)
        elements = driver.find_elements(By.XPATH, '//*[@id="articles-list"]/article')
        df = pd.DataFrame(columns=['title', 'date', 'url', 'paywall', 'summary', 'author', 'theme'])
        for element in elements:
            article = {}
            soup = BeautifulSoup(element.get_attribute('innerHTML'), 'html.parser')
            article['title'] = soup.find('h2').text.strip()
            print(article['title']) if DEBUG else None
            article['date'] = dateparser.parse(soup.find('time').text.split('le')[1].replace('à','at'))
            print(f"date found: {soup.find('time').text.split('le')[1]}") if DEBUG else None
            print(article['date']) if DEBUG else None
            try:
                article['theme'] = soup.find('ul').find_all('li')[1].find('a').text.strip()
                print(article['theme']) if DEBUG else None
            except:
                article['theme'] = ''
                print('No theme') if DEBUG else None
            try:
                article['summary'] = soup.find_all('div')[-1].text.strip()
                print(article['summary']) if DEBUG else None
            except:
                article['summary'] = ''
                print('No summary') if DEBUG else None
            article['url'] = soup.find('h2').find('a').get('href')
            print(article['url']) if DEBUG else None
            article['paywall'] = 'Réservé aux abonnés' in element.get_attribute('innerHTML')
            print(article['paywall']) if DEBUG else None
            print(article) if DEBUG else None
            df.loc[len(df)+1]=article
        print('closing driver') if DEBUG else None
        driver.close()
        driver.quit()
        return df
    except Exception as e:
        print('error') if DEBUG else None
        print(e) if DEBUG else None
        print('closing driver') if DEBUG else None
        driver.close()
        driver.quit()
        return None

def article_contents(urls, cookie_file, DEBUG=False):
    try:
        print('setting options') if DEBUG else None
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--no-sandbox')
        print('opening driver') if DEBUG else None
        cookie_jar = parse_netscape_cookie_file(cookie_file)

        driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=options)
        
        width = 1920 # in pixels
        height = 1080 # in pixels
        driver.set_window_size(width, height)

        print('adding cookies') if DEBUG else None

        print('getting first page') if DEBUG else None
        # Open a page before adding cookies
        driver.get(URL_LOGIN)

        articles = []
        for url in urls:
            try:
                print(f'getting page {url}') if DEBUG else None
                add_cookies_to_driver(driver, cookie_jar)# Add cookies to WebDriver
                driver.get(url)
                
                print('scrolling') if DEBUG else None
                scroll(driver)
                print('saving screenshot post scroll') if DEBUG else None
                save_screenshot(driver, os.path.join(PWD,'screen_article_step3.png')) if DEBUG else None
                print('getting html') if DEBUG else None

                #extracting text
                element = driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div/article')
                
                soup = BeautifulSoup(element.get_attribute('innerHTML'), 'html.parser')
                elements = soup.find_all(['h2', 'p'])

                #Concatenate texts but like not shit text
                combined_text = ' '.join(element.get_text() for element in elements)
                print(combined_text) if DEBUG else None
                articles.append({'url':url, 'text':combined_text})
                print('finished with this article') if DEBUG else None
            except Exception as e:
                print('error') if DEBUG else None
                print(e) if DEBUG else None
        driver.close()
        driver.quit()
        return articles
    except:
        print('error') if DEBUG else None
        print('closing driver') if DEBUG else None
        driver.close()
        driver.quit()
        return None