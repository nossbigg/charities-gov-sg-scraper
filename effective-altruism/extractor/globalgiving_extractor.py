import csv
import itertools
import json

import urllib3
from bs4 import BeautifulSoup

GLOGALGIVING_SEARCH_URL = 'https://www.globalgiving.org/search/'
GLOBALGIVING_API_URL = \
    'https://www.globalgiving.org/dy/v2/search/query'

GLOBALGIVING_CSV_DUMP_PATH = '../data/globalgiving.csv'
GLOBALGIVING_JSON_DUMP_PATH = '../data/globalgiving.json'


class GlobalGivingExtractor:
    http = urllib3.PoolManager()

    def do_scrape(self):
        charities = self.get_charities()

        charities_column_names_standardized = self.convert_to_standardized_columns(
            charities)
        charities_with_merged_programs = \
            self.merge_programs_from_common_charities(charities_column_names_standardized)

        self.write_list_as_json_to_file(GLOBALGIVING_JSON_DUMP_PATH,
                                        charities_with_merged_programs)
        self.write_list_as_csv_to_file(GLOBALGIVING_CSV_DUMP_PATH,
                                       charities_with_merged_programs)

    def get_charities(self):
        number_of_charities = self.get_number_of_charities()

        charities_raw = self.get_charities_json_from_api(number_of_charities)

        charities = charities_raw['hits']['hits']
        charities = [charity['_source'] for charity in charities]

        return charities

    def get_number_of_charities(self):
        query_parameters = self.generate_search_api_query_parameters(1)
        request = self.http.request('POST', GLOBALGIVING_API_URL, fields=query_parameters)
        request_json = json.loads(request.data)
        return request_json['hits']['total']

    def get_charities_json_from_api(self, count):
        query_parameters = self.generate_search_api_query_parameters(count)
        request = self.http.request('POST', GLOBALGIVING_API_URL, fields=query_parameters)
        request_json = json.loads(request.data)
        return request_json

    def get_cause_area_converter(self):
        request = self.http.request('POST', GLOGALGIVING_SEARCH_URL)
        request_html_body = request.data.decode("UTF-8")

        soup = BeautifulSoup(request_html_body, 'html.parser')

        filter_tabs = soup.find_all("div", class_="grid-parent box_horizontalPadded1 box_padded2 "
                                                  "box_md_padded3 layout_rel filterBar-filter")
        theme_filter_tab = filter_tabs[1]

        themes_labels = theme_filter_tab.find_all('label')
        themes = {}
        for theme in themes_labels:
            theme_shorthand = theme['for']
            theme_full_description = theme['data-displayname']
            themes[theme_shorthand] = theme_full_description

        return themes

    @staticmethod
    def generate_search_api_query_parameters(search_size):
        return {
            'size': search_size,
            'nextPage': 0,
            'sortField': 'sortorder',
            'keywords': '',
        }

    def convert_to_standardized_columns(self, charities):
        cause_area_converter = self.get_cause_area_converter()
        columns_to_keep = ["name", "cause_area", "country", "description"]

        for charity in charities:
            charity['name'] = charity.get('orgname', '')
            charity['country'] = charity.get('countryname', '')
            charity['description'] \
                = charity.get('projtitle', '') + ": " + charity.get('projsummary', '')

            cause_areas = charity.get('allthemes', [])
            cause_areas = [cause_area_converter[cause_area] for cause_area in cause_areas]
            charity['cause_area'] = ", ".join(cause_areas)

            for column_name in list(charity.keys()):
                if column_name not in columns_to_keep:
                    del charity[column_name]

        return charities

    @staticmethod
    def merge_programs_from_common_charities(charities_column_names_standardized):
        charities_merged = {}

        for charity in charities_column_names_standardized:
            charity_name = charity['name']

            if charity_name not in charities_merged:
                charities_merged[charity_name] = charity
                continue

            existing_charity = charities_merged[charity_name]

            merged_charity = {
                'name': existing_charity['name'],
                'country': existing_charity['country'] + ", " + charity['country'],
                'description': existing_charity['description'] + ", " + charity['description'],
                'cause_area': existing_charity['cause_area'] + ", " + charity['cause_area'],
            }

            charities_merged[charity_name] = merged_charity

        return list(charities_merged.values())

    @staticmethod
    def get_all_possible_fieldnames(list_of_dicts):
        keys_flattened = list(itertools.chain.from_iterable(list_of_dicts))
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
