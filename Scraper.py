import csv
import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException, WebDriverException
from functools import wraps
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager


def retries(max_retries=3, delay=2, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    print(f"Function '{func.__name__}' crashed on attempt {attempts}/{max_retries}: {e}")
                    if attempts < max_retries:
                        print(f"Retrying function '{func.__name__}'...")
                        time.sleep(delay)
                    else:
                        print(f"Function '{func.__name__}' failed after {max_retries} retries.")
                        raise
        return wrapper
    return decorator

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def extract_and_convert_ordinal(text):
        number_to_words = {
            "1": "First", "2": "Second", "3": "Third", "4": "Fourth", "5": "Fifth", 
            "6": "Sixth", "7": "Seventh", "8": "Eighth", "9": "Ninth", "10": "Tenth",
            "11": "Eleventh", "12": "Twelfth", "13": "Thirteenth", "14": "Fourteenth", 
            "15": "Fifteenth", "16": "Sixteenth", "17": "Seventeenth", "18": "Eighteenth", 
            "19": "Nineteenth", "20": "Twentieth", "21": "Twenty First", "22": "Twenty Second",
            "23": "Twenty Third", "24": "Twenty Fourth", "25": "Twenty Fifth", "26": "Twenty Sixth",
            "27": "Twenty Seventh", "28": "Twenty Eighth", "29": "Twenty Ninth", "30": "Thirtieth"
        }

        words = text.split()
        for word in words:
            if word.isdigit() or (word[:-2].isdigit() and word[-2:] in ["ST", "ND", "RD", "TH"]):
                key = word[:-2] if word[:-2].isdigit() else word
                return number_to_words.get(key, word)
        return text

def parse_address(address):
    # Split the address
    address_parts = address.split(",")
    
    street = address_parts[0].strip().split(" ")
    state_info = address_parts[-1].strip().split(" ") if len(address_parts) > 1 else ""

    # Split the street values
    if len(street) < 2:
         return {
        'street_no': '',
        'street_name': '',
        'city': '',
        'state': '',
        'zip': '',
    }
    street_no = street[0] if len(street) > 0 else ''
    print('street ' , street)
    street_name = None
    if len(street[1]) > 1:
        street_name = extract_and_convert_ordinal(street[1])
    elif len(street) > 2 :
        street_name = extract_and_convert_ordinal(street[2])

    # Split the state information
    city = state_info[0] if len(state_info) > 0 else ''
    state = state_info[1] if len(state_info) > 1 else ''
    zip_code = state_info[2] if len(state_info) > 2 else ''  # Assuming zip is at index 2

    return {
        'street_no': street_no,
        'street_name': street_name,
        'city': city,
        'state': state,
        'zip': zip_code,
    }


@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def get_chromedriver(headless=False):
    print("Initializing Chrome WebDriver...")
    current_dir = os.getcwd()  # Get current working directory for downloads
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": current_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--start-maximized")
    if headless:
        chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    pid = driver.service.process.pid
    print(f"Chrome WebDriver initialized. Process ID: {pid}")
    return driver, pid


def get_case_rows(driver):
    cases_list = []
    try:
        xpath = "//table[@bgcolor='black']//tr[td/font[normalize-space(text()) = 'FULL ADMINISTRATION WITH WILL' or normalize-space(text()) = 'FULL ADMINISTRATION WITHOUT WILL']]/td[1]/a"
        case_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath))
        )
        for case in case_elements:
            cases_list.append(case.text.strip() if case is not None else None)
        print(f"Found {len(cases_list)} cases.")
    except TimeoutException:
        print("Timeout: Unable to find case rows within the specified time.")
    except NoSuchElementException:
        print("Error: No elements found matching the criteria.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return cases_list


def extract_fields(chrome, fields, data):
    for field in fields:
        try:
            element = WebDriverWait(chrome, 5).until(
                EC.presence_of_element_located((By.XPATH, field["xpath"]))
            )
            data[field["key"]] = element.text.strip()
            if field.get("description"):
                print(f"{field['description']}: {element.text.strip()}")
        except TimeoutException:
            data[field["key"]] = ""
            if field.get("description"):
                print(f"{field['description']} not found.")
        except Exception as e:
            print(f"Error extracting field {field['key']}: {e}")


def parse_name(data, key, prefix=""):
    try:
        if data.get(key):
            name_parts = data[key].split(", ")
            first_middle = name_parts[1].split(" ") if len(name_parts) > 1 else []
            data[f"{prefix}_first_name"] = first_middle[0] if len(first_middle) > 0 else ""
            data[f"{prefix}_middle_name"] = first_middle[1] if len(first_middle) > 1 else ""
            data[f"{prefix}_last_name"] = name_parts[0] if len(name_parts) > 0 else ""
    except Exception as e:
        print(f"Error parsing name {key}: {e}")


def process_case_data(chrome, case):
    if not case:
        return {}

    case = case.strip()
    print(f"Processing case: {case}")
    case_data = {"caseno": case}

    try:

        # URLs
        case_url = f'http://probatesearch.franklincountyohio.gov/netdata/PBCaseTypeE.ndm/ESTATE_DETAIL?caseno={case};;'
        admin_url = f'https://probatesearch.franklincountyohio.gov/netdata/PBFidy.ndm/input?caseno={case};;'

        # Navigate to the case URL
        try:
            chrome.get(case_url)
            case_data['case_url'] = case_url
            time.sleep(1)
        except WebDriverException as e:
            print(f"Error navigating to case URL: {e}")
            case_data['case_url'] = case_url
            return case_data

        # Define XPaths for case details
        case_fields = [
            {"xpath": "//tr[th/font[normalize-space(text()) = 'Case Name']]/td/font", "key": "case_name", "description": "Case Name"},
            {"xpath": "//tr[th/font[normalize-space(text()) = 'Case Subtype']]/td/font", "key": "case_subtype", "description": "Case Subtype"},
            {"xpath": "//tr[th/font[normalize-space(text()) = 'Decedent Street']]/td/font", "key": "decendent_address", "description": "Decedent Address"},
            {"xpath": "//tr[th/font[normalize-space(text()) = 'City']]/td/font", "key": "decendent_city", "description": "Decedent City"},
            {"xpath": "//tr[th/font[normalize-space(text()) = 'State']]/td/font", "key": "decendent_state", "description": "Decedent State"},
            {"xpath": "//tr[th/font[normalize-space(text()) = 'Zip']]/td/font", "key": "decendent_zip", "description": "Decedent Zip Code"},
        ]

        # Extract case details
        try:
            extract_fields(chrome, case_fields, case_data)
        except Exception as e:
            print(f"Error extracting case details: {e}")

        # Parse case name into parts
        try:
            parse_name(case_data, "case_name", prefix="decendent")
        except Exception as e:
            print(f"Error parsing case name: {e}")

        # Navigate to admin URL
        try:
            print("Navigating to admin site...")
            chrome.get(admin_url)
            case_data['view_state_link'] = admin_url
            admins = WebDriverWait(chrome, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//table[@bgcolor="black"]/tbody/tr[@bgcolor != "#07528B"]'))
            )
        except (TimeoutException, WebDriverException) as e:
            print(f"Error navigating to admin site or fetching admins: {e}")
            return case_data

        # Process each admin
        for i, _ in enumerate(admins):
            try:
                fiduciary_url = f'https://probatesearch.franklincountyohio.gov/netdata/PBFidDetail.ndm/FID_DETAIL?caseno={case};;{i}'
                chrome.get(fiduciary_url)
                admin_fields = [
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'Estate Fiduciaries Name']]/td/font", "key": "admin_name", "description": "Admin Name"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'Street']]/td/font", "key": "admin_address", "description": "Admin Address"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'City']]/td/font", "key": "admin_city", "description": "Admin City"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'State']]/td/font", "key": "admin_state", "description": "Admin State"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'Zip']]/td/font", "key": "admin_zip", "description": "Admin Zip Code"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'Phone Number']]/td/font", "key": "admin_phone", "description": "Admin Phone Number"},
                ]
                extract_fields(chrome, admin_fields, case_data)
                parse_name(case_data, "admin_name", prefix="admin")
            except Exception as e:
                print(f"Error processing admin data: {e}")

            # Attorney details
            try:
                attorney_url = f'https://probatesearch.franklincountyohio.gov/netdata/PBAttyDetail.ndm/ATTY_DETAIL?caseno={case};;{i}'
                chrome.get(attorney_url)
                attorney_fields = [
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'Attorney Name']]/td/font", "key": "attorney_name", "description": "Attorney Name"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'Phone Number']]/td/font", "key": "attorney_phone", "description": "Attorney Phone Number"},
                    {"xpath": "//tr[th/font[normalize-space(text()) = 'E-mail Address']]/td/font", "key": "attorney_email", "description": "Attorney Email"},
                ]
                extract_fields(chrome, attorney_fields, case_data)
                parse_name(case_data, "attorney_name", prefix="attorney")
            except Exception as e:
                print(f"Error processing attorney data: {e}")

        return case_data

    except Exception as e:
        print(f"Unexpected error in get_case_data: {e}")
        return case_data



def process_all_cases(chrome, cases):
    all_cases_data = []
    for case in cases:
        try:
            case_data = process_case_data(chrome, case)
            print("caseData is : " ,  case_data)
            all_cases_data.append(case_data)
        except Exception as e:
            print(f"Error processing case {case}: {e}")
    return all_cases_data


def save_to_csv(rows, filename):
    fieldnames = [
        "case_num", "parcel_number", "decendent_first_name", "decendent_middle_name", "decendent_last_name",
        "sub_type", "case_link", "d_property_address", "d_property_city", "d_property_state", "d_property_zip",
        "view_state_link", "admin_first_name", "admin_middle_name", "admin_last_name", "admin_address", "admin_city",
        "admin_state", "admin_zip", "admin_phone", "att_first_name", "att_middle_name", "att_last_name", "att_phone", "att_email"
    ]
    try:
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def search_and_get_case_data(driver, case_data ):
    try:
        # Parse the address
        parsed_address = parse_address(case_data['decendent_address'])

        if parsed_address['street_no'] == '' and parsed_address['street_name'] == '':
            return case_data
        print('parse_address ' , parsed_address)
        print("Opened the browser")

        # Fill out search form
        def fill_input(xpath, value, field_name):
            try:
                input_field = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                input_field.send_keys(value)
                print(f"{field_name} input sent: {value}")
            except TimeoutException:
                print(f"{field_name} input field not found.")

        fill_input('//input[@id="inpNumber"]', parsed_address['street_no'], "Street Number")
        fill_input('//input[@id="inpStreet"]', parsed_address['street_name'], "Street Name")

        # Click the search button
        try:
            search_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@id="btSearch"]'))
            )
            search_btn.click()
            print("Clicked the Search Button")
        except TimeoutException:
            print("Search button not found.")
            return

        time.sleep(3)

        # Check for "No Records Found" error
        try:
            WebDriverWait(driver, 11).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//large[contains(text(), "Your search did not find any records")]')
                )
            )
            print("No records found for the search.")
            # beds,bathrooms,Tot Fin Area,Yr Built,transfer date,transfer price
            case_data.update({
                'beds': 'N/A',
                'bathrooms': 'N/A',
                'Tot Fin Area': 'N/A',
                'Yr Built': 'N/A',
                'transfer date': 'N/A',
                'transfer price': 'N/A'
            })
            return case_data
        except TimeoutException:
            print("Records found. Continuing...")

        
        try:
            record_table_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '(//table[@id="searchResults"]/tbody/tr)[1]'))
            )
            record_table_btn.click()
            print("Clicked the First Row")
        except TimeoutException:
            print("Search Results timed out")


        # Helper function to extract data with XPath
        def extract_data(xpath, key, description=None):
            try:
                element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                if key == 'parcel_id':
                    case_data[key] = element.text.split(':')[1].strip()
                else:
                    case_data[key] = element.text.strip()
                if description:
                    print(f"{description}: {element.text.strip()}")
            except TimeoutException:
                case_data[key] = ""
                if description:
                    print(f"{description} not found.")

        extract_data('//td[@class="DataletHeaderTopLeft"]', 'parcel_id', "Parcel ID")
        # Dwelling data
        dwelling_data = {
            '(//table[@id="Dwelling Data"]//td)[10]': 'bedrooms',
            '(//table[@id="Dwelling Data"]//td)[11]': 'bathrooms',
            '(//table[@id="Dwelling Data"]//td)[8]': 'Tot Fin Area',
            '(//table[@id="Dwelling Data"]//td)[7]': 'Year built'
        }
        for xpath, key in dwelling_data.items():
            extract_data(xpath, key, key)

        # Transfer details
        extract_data('//tr[td[contains(text(), "Transfer Date")]]/td[@class="DataletData"]',
                     'Transfer Date', "Transfer Date")
        extract_data('//tr[td[contains(text(), "Transfer Price")]]/td[@class="DataletData"]',
                     'Transfer Price', "Transfer Price")
        # beds,bathrooms,Tot Fin Area,Yr Built,transfer date,transfer price

        return case_data

    except Exception as e:
        print(f"An error occurred while searching for the address: {e}")
        return case_data

def preprocess_case_data(all_data, processed_data):
    for item in all_data:
        if item is None:
            continue

        # Map fields to required output columns
        processed_data.append({
            "case_num": item.get('caseno', ''),
            "parcel number": item.get('parcel_id', ''),  # Assuming 'parcel_id' exists or leave blank
            "decendent_first_name": item.get('decendent_first_name', ''),
            "decendent_middle_name": item.get('decendent_middle_name', ''),
            "decendent_last_name": item.get('decendent_last_name', ''),
            "sub_type": item.get('case_subtype', ''),
            "case_link": item.get( "case_url", ''),
            "d_property_address": item.get('decendent_address', ''),
            "d_property_city": item.get('decendent_city', ''),
            "d_property_state": item.get('decendent_state', ''),
            "d_property_zip": item.get('decendent_zip', ''),
            "view_state_link": item.get('view_state_link', ''),
            "admin_first_name": item.get('admin_first_name', ''),
            "admin_middle_name": item.get('admin_middle_name', ''),
            "admin_last_name": item.get('admin_last_name', ''),
            "admin_address": item.get('admin_address', ''),
            "admin_city": item.get('admin_city', ''),
            "admin_state": item.get('admin_state', ''),
            "admin_zip": item.get('admin_zip', ''),
            "admin_phone": item.get('admin_phone', ''),
            "att_first_name": item.get('attorney_first_name', ''),
            "att_middle_name": item.get('attorney_middle_name', ''),
            "att_last_name": item.get('attorney_last_name', ''),
            "att_phone": item.get('attorney_phone', ''),
            "att_email": item.get('attorney_email', ''),
            "beds": item.get('bedrooms', ''),
            "bathrooms": item.get('bathrooms', ''),
            "Tot Fin Area": item.get('Tot Fin Area', ''),
            "Yr Built": item.get('Year built', ''),
            "transfer date": item.get('Transfer Date', ''),
            "transfer price": item.get('Transfer Price', '')
        })



if __name__ == "__main__":
    date = input("Enter a date in the format YYYYMMDD:\t ")
    url = f'https://probatesearch.franklincountyohio.gov/netdata/PBODateInx.ndm/input?string={date}'
    print("Url : \n" , url)
    try:
        print("Getting the Chrome Driver...")
        driver, pid = get_chromedriver(headless=True)
        driver.get(url)
        print("Fetching case rows...")
        cases = get_case_rows(driver)
        print(f"Total cases found: {len(cases)}")
        all_data = []
        unprocessed_data = []
        if cases:
            all_data = process_all_cases(driver, cases)
            # save_to_csv(all_data, "case_data.csv")
        for data in all_data:
            driver.get("https://property.franklincountyauditor.com/_web/search/commonsearch.aspx?mode=address")
            unprocessed_data.append(search_and_get_case_data(driver, data))

            print('data is data' , data)
        print("Processing complete.")

        processed_case_data = []
    
        try:
            # Process individual case data
            preprocess_case_data(unprocessed_data, processed_case_data)  # Using the reference `process_case_data` function
        except Exception as e:
            print(f"[{datetime.now()}] Error processing case : ")
    
        COLUMN_NAMES = [
            "case_num", "parcel number", "decendent_first_name", "decendent_middle_name", "decendent_last_name",
            "sub_type", "case_link", "d_property_address", "d_property_city", "d_property_state", "d_property_zip",
            "view_state_link", "admin_first_name", "admin_middle_name", "admin_last_name", "admin_address", "admin_city",
            "admin_state", "admin_zip", "admin_phone", "att_first_name", "att_middle_name", "att_last_name", "att_phone",
            "att_email", "beds", "bathrooms", "Tot Fin Area", "Yr Built", "transfer date", "transfer price"
        ]

        csv_filename = "case_data.csv"
        df = pd.DataFrame(processed_case_data , columns=COLUMN_NAMES)
        if os.path.exists(csv_filename):
            if os.path.exists('Previous_data.csv'):
                os.remove('Previous_data.csv')
            os.rename(csv_filename , 'Previous_data.csv')

        df.to_csv(csv_filename, index=False)
        print(f"[{datetime.now()}] All data saved to {csv_filename}")

        print(f"[{datetime.now()}] Processing complete.")
    except Exception as e:
        print(f"An error occurred in the main process: {e}")
    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error closing the driver: {e}")
