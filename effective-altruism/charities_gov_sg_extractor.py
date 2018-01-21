import itertools
import json
import math
import re

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

SELENIUM_CHROME_DRIVER_PATH = './selenium_drivers/chromedriver'

CHARITIES_GOV_SG_URL = \
    'https://www.charities.gov.sg/_layouts/MCYSCPSearch/MCYSCPSearchCriteriaPage.aspx'

REGISTERED_CHARITIES_JSON_DUMP_PATH = './data/charitiesgovsg.json'
REGISTERED_CHARITIES_CSV_DUMP_PATH = './data/charitiesgovsg.csv'
CSV_DELIMITER = "|"


def do_scrape():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('headless')
    browser = webdriver.Chrome(
        executable_path=SELENIUM_CHROME_DRIVER_PATH,
        chrome_options=chrome_options)

    registered_charities = scrape_registered_charities(browser)
    write_list_as_json_to_file(REGISTERED_CHARITIES_JSON_DUMP_PATH, registered_charities)
    write_list_as_csv_to_file(REGISTERED_CHARITIES_CSV_DUMP_PATH, registered_charities)


def scrape_registered_charities(browser):
    page_tables = []

    browser.get(CHARITIES_GOV_SG_URL)

    search_button_xpath = '//*[@id="ctl00_PlaceHolderMain_btnSearch"]'
    move_to_and_click_element(browser, search_button_xpath)

    wait_for_page_load(browser)
    current_page = get_current_page(browser)

    expected_pages = get_expected_pages(browser)
    print('Expected pages: ' + str(expected_pages))

    while True:
        print('Current page: ' + str(current_page))

        page_tables.append(extract_current_page_table(browser))

        if not has_next_page(browser, current_page):
            break

        go_to_next_page(browser, current_page)
        wait_for_page_load(browser)
        current_page = get_current_page(browser)

    charities_unflattened = [extract_charities(page_table) for page_table in page_tables]
    charities = list(itertools.chain.from_iterable(charities_unflattened))

    if current_page < expected_pages:
        print('Warning: Did not reach last page')

    return charities


def extract_current_page_table(browser):
    table_parent_element_xpath = '//*[@id="ctl00_PlaceHolderMain_divSearchResult"]'
    table_parent_element = browser.find_element_by_xpath(table_parent_element_xpath)
    return table_parent_element.get_attribute('innerHTML')


def extract_charities(page_table_html):
    charities = []

    soup = BeautifulSoup(page_table_html, 'html.parser')
    charity_tr_class = \
        re.compile('ctl00_PlaceHolderMain_lstSearchResults_ctrl[0-9]+_trSearchDataList')
    matched_charities_tag = soup.find_all('tr', id=charity_tr_class)
    for index in range(0, len(matched_charities_tag)):
        charity_tr_tag = matched_charities_tag[index]
        charities.append(extract_charity_from_tr(charity_tr_tag, index))

    return charities


def extract_charity_from_tr(charity_tr_tag, index):
    index = str(index)
    return {
        'Name of Organization':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblNameOfOrg').text.strip(),
        'UEN No':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblUENNo').text.strip(),
        'Charity Status':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblCharityStatus').text.strip(),
        'Date of Charity Registration':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblDateOfCharityReg').text.strip(),
        'IPC Status':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblIPCStatus').text.strip(),
        'IPC Period':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblIPCPeriodNo').text.strip(),
        'Address':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblAddress').text.strip(),
        'Website':
            charity_tr_tag.find('a',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblOrgWebsite').text.strip(),
        'Primary sector':
            charity_tr_tag.find('span',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_lblSector').text.strip(),
        'Details URL':
            charity_tr_tag.find('input',
                                id='ctl00_PlaceHolderMain_lstSearchResults_ctrl' + index + '_hfViewDetails')[
                'value'].strip()
    }


# HELPER FUNCTIONS
def go_to_next_page(browser, current_page):
    back_to_top_xpath = '//*[@id="backToTop"]'
    move_to_element(browser, back_to_top_xpath)

    next_page_element_xpath = generate_next_page_element_xpath(current_page)
    move_to_and_click_element(browser, next_page_element_xpath)


def get_current_page(browser):
    current_page_css_selector = 'span#ctl00_PlaceHolderMain_spPager1 > span'
    current_page = browser \
        .find_element_by_css_selector(current_page_css_selector) \
        .text

    return int(current_page)


def generate_next_page_element_xpath(current_page):
    return '//*[@id="ctl00_PlaceHolderMain_spPager1"]/a[text()=\'' + str(current_page + 1) + '\']'


def has_next_page(browser, current_page):
    next_page_element_xpath = generate_next_page_element_xpath(current_page)
    try:
        browser.find_element_by_xpath(next_page_element_xpath)
        return True
    except NoSuchElementException:
        return False


def get_expected_pages(browser):
    search_results_css_selector = 'span#ctl00_PlaceHolderMain_lblSearchCount'
    search_results = browser \
        .find_element_by_css_selector(search_results_css_selector) \
        .text

    results_per_page = 5
    total_records = int(search_results.split(' ')[0])
    expected_pages = math.ceil(total_records / results_per_page)

    return int(expected_pages)


def wait_for_page_load(browser):
    pagination_css_selector = 'span#ctl00_PlaceHolderMain_spPager1'
    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, pagination_css_selector)))


def move_to_and_click_element(browser, element_xpath):
    element = browser.find_element_by_xpath(element_xpath)

    webdriver.ActionChains(browser) \
        .move_to_element(element) \
        .click(element) \
        .perform()


def move_to_element(browser, element_xpath):
    element = browser.find_element_by_xpath(element_xpath)

    webdriver.ActionChains(browser) \
        .move_to_element(element) \
        .perform()


def write_list_as_json_to_file(filepath, list_of_dicts):
    with open(filepath, 'w') as file_out:
        json.dump(list_of_dicts, file_out)


def write_list_as_csv_to_file(filepath, list_of_dicts):
    df = pd.DataFrame(list_of_dicts)
    df.to_csv(filepath,
              sep=CSV_DELIMITER,
              index=False,
              encoding='utf-8')


do_scrape()
