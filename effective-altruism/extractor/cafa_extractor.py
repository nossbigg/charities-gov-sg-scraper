import csv
import itertools
import json
import re
from string import Template

import urllib3
from bs4 import BeautifulSoup, Tag, NavigableString

CAFA_API_URL = \
    'https://cafa.iphiview.com/cafa/API/EnhancedCharitySearch/' \
    'dagenhancedcharitysearchbyfocusandgeographicarea'

CAFA_JSON_DUMP_PATH = '../data/cafa.json'
CAFA_CSV_DUMP_PATH = '../data/cafa.csv'


class CafaExtractor:
    http = urllib3.PoolManager()

    def do_scrape(self):
        charities = self.get_charities()
        charities_with_details = self.get_charities_detailed(charities)

        charities_column_names_standardized = self.convert_to_standardized_columns(
            charities_with_details)

        self.write_list_as_json_to_file(CAFA_JSON_DUMP_PATH, charities_column_names_standardized)
        self.write_list_as_csv_to_file(CAFA_CSV_DUMP_PATH, charities_column_names_standardized)

    def get_number_of_charities(self):
        query_parameters = self.generate_default_query_parameters()
        request = self.http.request('POST', CAFA_API_URL, fields=query_parameters)
        request_json = json.loads(request.data)
        return request_json['Count']

    def get_charities(self):
        number_of_charities = self.get_number_of_charities()

        charities_unflattened = \
            [self.get_charities_by_pagination(start_index)
             for start_index in range(0, number_of_charities, 10)]
        charities_flattened = list(itertools.chain.from_iterable(charities_unflattened))

        return charities_flattened

    def get_charities_by_pagination(self, start_index):
        query_parameters = self.generate_default_query_parameters()
        query_parameters['startIndex'] = start_index
        request = self.http.request('POST', CAFA_API_URL, fields=query_parameters)
        request_json = json.loads(request.data)
        return request_json['Data']

    def get_charities_detailed(self, charities):
        return [{**charity, **self.get_charity_detailed_page(charity)}
                for charity in charities]

    def get_charity_detailed_page(self, charity):
        details_dispatch = charity['DetailsDispatch']
        charity_detailed_page_url = self.generate_charity_details_url(details_dispatch)

        request = self.http.request('GET', charity_detailed_page_url)
        request_html_body = request.data.decode("UTF-8")

        return self.get_charity_details_from_page_html(request_html_body)

    def get_charity_details_from_page_html(self, request_html_body):
        soup = BeautifulSoup(request_html_body, 'html.parser')

        charity_details = {
            'Organization FullAddress':
                self.get_html_element_null_safe(soup, 'div', "Organization FullAddress"),
            'Organization Url':
                self.get_html_element_null_safe(soup, 'div', "Organization Url")}
        charity_details['Organization Url'] \
            = charity_details['Organization Url'].replace("Website: ", "")

        charity_details = {
            **charity_details,
            **self.get_charity_communications(soup),
            **self.get_charity_text_details(soup)
        }

        return charity_details

    @staticmethod
    def convert_to_standardized_columns(charities):
        columns_to_keep = ["name", "website", "cause_area", "description",
                           "address", "email", "contact_number"]

        for charity in charities:
            charity['name'] = charity.get('Name', '')
            charity['website'] = charity.get('Organization Url', '')
            charity['cause_area'] = charity.get('FieldsOfInterest', '')
            charity['description'] \
                = charity.get('Organization Mission', ' ') \
                  + charity.get('Organization Summary', ' ') \
                  + charity.get('Organization Background', ' ') \
                  + charity.get('How will a grant make a difference', ' ')
            charity['address'] = charity.get('Organization FullAddress', '')
            charity['email'] = charity.get('Email', ' ') + charity.get('Work EMail', ' ') \
                               + charity.get('email', ' ')
            charity['contact_number'] \
                = charity.get('Direct Phone', ' ') + charity.get('Direct Fax', ' ') \
                  + charity.get('Office Fax', ' ') + charity.get('Cell Phone', ' ') \
                  + charity.get('Office General', ' ') + charity.get('Work Phone', ' ') \
                  + charity.get('Work Fax', ' ') + charity.get('Employers Phone', ' ') \
                  + charity.get('Home Fax', ' ')

            for column_name in list(charity.keys()):
                if column_name not in columns_to_keep:
                    del charity[column_name]

        return charities

    @staticmethod
    def get_charity_communications(soup):
        communications_div = soup.find("div", class_="AllCommunications")
        if communications_div is None:
            return {}

        communications_details = {}
        communications_trs = communications_div.find_all("tr")
        for tr in communications_trs:
            communication_field = tr.contents[0].text
            communication_field = re.sub("[^a-zA-Z0-9 ]", "", communication_field)

            communication_field_detail = tr.contents[1].text

            communications_details[communication_field] = communication_field_detail

        return communications_details

    def get_charity_text_details(self, soup):
        dl_element = soup.find("dl")
        if dl_element is None:
            return {}

        dt_elements = dl_element.find_all("dt", recursive=False)

        text_details = {}
        for dt in dt_elements:
            dt_title = dt.text
            dt_title = re.sub("[^a-zA-Z0-9 ]", "", dt_title)
            dt_contents = self.get_text_from_element(dt.nextSibling)
            dt_contents = re.sub("[\n\r]", "", dt_contents)

            text_details[dt_title] = dt_contents

        return text_details

    @staticmethod
    def get_text_from_element(element):
        if isinstance(element, Tag):
            return element.text
        elif isinstance(element, NavigableString):
            return element.string
        else:
            return ""

    @staticmethod
    def get_html_element_null_safe(soup, html_element_type, html_element_class):
        element = soup.find(html_element_type, class_=html_element_class)

        if element is None:
            return ""

        return element.text

    @staticmethod
    def generate_charity_details_url(details_dispatch):
        charity_details_url_template = Template(
            'https://cafa.iphiview.com/cafa/Organizations/OrganizationView/tabid/437/'
            'dispatch/$details_dispatch/Default.aspx')
        return charity_details_url_template.substitute(details_dispatch=details_dispatch)

    @staticmethod
    def generate_default_query_parameters():
        return {
            'startIndex': 0,
            'pageSize': 10,
            'sortExpressions': 'Name ASC',
            'isPaged': 'true',
            'format': 'json',
            'dispatch': 'dagenhancedcharitysearchbyfocusandgeographicarea'
                        '_focusArea$0_geographicArea$10004_country$0'
        }

    @staticmethod
    def get_all_possible_fieldnames(list_of_dicts):
        keys_unflattened = [d.keys() for d in list_of_dicts]
        keys_flattened = list(itertools.chain.from_iterable(keys_unflattened))
        return set(keys_flattened)

    @staticmethod
    def write_list_as_json_to_file(filepath, list_of_dicts):
        with open(filepath, 'w') as file_out:
            json.dump(list_of_dicts, file_out)

    def write_list_as_csv_to_file(self, filepath, list_of_dicts):
        with open(filepath, mode='w', newline="\n") as csv_file:
            fieldnames = self.get_all_possible_fieldnames(list_of_dicts)
            csv_file_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            csv_file_writer.writeheader()
            for charity in list_of_dicts:
                csv_file_writer.writerow(charity)
