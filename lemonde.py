import json
import time
from selenium.webdriver.common.by import By
import html_to_json
from selenium import webdriver
import pandas as pd
import dateparser
import os 
from bs4 import BeautifulSoup
import http.cookiejar

PWD = os.path.abspath(os.getcwd())
URL = "https://www.lemonde.fr/recherche/"
URL_LOGIN = "https://www.lemonde.fr/"
#Thanks to https://stackoverflow.com/questions/41721734/take-screenshot-of-full-page-with-selenium-python-with-chromedriver
def save_screenshot(driver: webdriver.Chrome, path: str = '/mnt/2To/jupyter_data/socc/screenie.png') -> None:
    original_size = driver.get_window_size()
    required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
    required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
    driver.set_window_size(required_width, required_height)
    driver.find_element(By.XPATH,'//*[@id="js-body"]').screenshot(path)  # avoids scrollbar
    driver.set_window_size(original_size['width'], original_size['height'])

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


def fetch_lemonde(SEARCH, DATE_FROM, DATE_TO, DEBUG=False):
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

        driver.get(URL)
        time.sleep(1)

        print('page loaded') if DEBUG else None
        print('saving screenshot pre cookie') if DEBUG else None
        save_screenshot(driver, os.path.join(PWD,'screen_step0.png')) if DEBUG else None

        try:
            print('accepting cookies') if DEBUG else None
            driver.find_element(By.XPATH, "/html/body/div[6]/div/footer/button").click()
        except:
            print("Cookies already accepted") if DEBUG else None

        print('saving screenshot post cookie') if DEBUG else None
        save_screenshot(driver, os.path.join(PWD,'screen_step1.png')) if DEBUG else None


        ## Search
        driver.find_element(By.XPATH, '//*[@id="search_keywords"]').send_keys(SEARCH)
        ### Date
        driver.find_element(By.XPATH, '//*[@id="search-container"]').click()
        driver.find_element(By.XPATH, '//*[@id="date-picker-start"]').clear()
        driver.find_element(By.XPATH, '//*[@id="date-picker-start"]').send_keys(DATE_FROM)
        driver.find_element(By.XPATH, '//*[@id="date-picker-end"]').clear()
        driver.find_element(By.XPATH, '//*[@id="date-picker-end"]').send_keys(DATE_TO)

        ### Submit
        driver.find_element(By.XPATH, '//*[@id="form-live-submit"]').click()
        
        time.sleep(1)
        print('saving screenshot end search') if DEBUG else None
        save_screenshot(driver, os.path.join(PWD,'screen_step2.png')) if DEBUG else None

        print('checking number of pages') if DEBUG else None
        try:
            print(driver.find_element(By.CLASS_NAME, "river__pagination").text) if DEBUG else None
            numb_page = len(driver.find_element(By.CLASS_NAME, "river__pagination").text.split("\n"))
        except:
            print("only one page") if DEBUG else None
            numb_page = 1
        print('number of pages : '+str(numb_page)) if DEBUG else None

        url = driver.current_url
        array = []
        for i in range(1,numb_page+1):
            url = url.split("&page=")[0]+"&page="+str(i)
            driver.get(url)
            print("url: "+url) if DEBUG else None
            time.sleep(1)
            print("page "+str(i)+" done") if DEBUG else None
            element = driver.find_element(By.XPATH, "/html/body/main/article/section/section/section[2]/section[3]").get_attribute('innerHTML')
            json_data = html_to_json.convert(element)
            array.append(json_data)

        print('closing driver') if DEBUG else None
        driver.close()
        driver.quit()
        return parser(array, DEBUG=DEBUG)
    except Exception as e:
        print('error') if DEBUG else None
        print(e) if DEBUG else None
        print('closing driver') if DEBUG else None
        driver.close()
        driver.quit()
        return None


def parser(array, DEBUG=False):
    df = pd.DataFrame(columns=['title', 'date', 'url', 'paywall', 'summary', 'author'])
    for json_data in array:
        for el in json_data['section']:
            if el['_attributes']['class'][0]=='teaser':
                title = el['a'][0]['h3'][0]['_value']
                print('title: ', title) if DEBUG else None
                url = el['a'][0]['_attributes']['href']
                paywall = True if len(el['a'][0]['span'])==2 else False
                summary = el['a'][0]['p'][0]['_value']
                author = None
                try:
                    author = el['p'][0]['span'][1]['_value']
                except:
                    print('no author') if DEBUG else None
                try:
                    date = dateparser.parse(el['p'][0]['span'][0]['_value'].split(',')[0].split('le')[1])
                except:
                    print(el['p'][0]['span'][0]['_value'])
                df.loc[len(df)+1]=({'title': title, 'date': date, 'url': url, 'paywall': paywall, 'summary': summary, 'author': author})
    return df


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
                element = driver.find_element(By.XPATH, '//*[@id="habillagepub"]/section/section/article')
                
                soup = BeautifulSoup(element.get_attribute('innerHTML'), 'html.parser')
                elements = soup.find_all(['h2', 'p'])

                #Concatenate texts but like not shit text
                combined_text = ' '.join(element.get_text() for element in elements)
                print(combined_text) if DEBUG else None
                articles.append({'url':url, 'text':combined_text})
                print('finished with this article') if DEBUG else None
                driver.implicitly_wait(10)
            except Exception as e:
                print(f'error was at url: {url}') if DEBUG else None
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