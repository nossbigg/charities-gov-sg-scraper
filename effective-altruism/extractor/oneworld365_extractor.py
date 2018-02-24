import csv
import itertools
import json

import urllib3

ONEWORLD365_API_URL = 'http://api.oneworld365.org/search/volunteer'

ONEWORLD365_CSV_DUMP_PATH = '../data/oneworld365.csv'
ONEWORLD365_JSON_DUMP_PATH = '../data/oneworld365.json'


class OneWorld365Extractor:
    http = urllib3.PoolManager()

    def do_scrape(self):
        charities = self.get_charities()

        charities_column_names_standardized = self.convert_to_standardized_columns(
            charities)

        self.write_list_as_json_to_file(ONEWORLD365_JSON_DUMP_PATH,
                                        charities_column_names_standardized)
        self.write_list_as_csv_to_file(ONEWORLD365_CSV_DUMP_PATH,
                                       charities_column_names_standardized)

    def get_charities(self):
        number_of_charities = self.get_number_of_charities()

        charities_raw = self.get_charities_json_from_api(number_of_charities)
        charities = charities_raw['data']['profile']

        return charities

    def get_number_of_charities(self):
        request_json = self.call_charities_api(1)

        return request_json['total_results']

    def get_charities_json_from_api(self, count):
        return self.call_charities_api(count)

    def call_charities_api(self, count=1):
        query_parameters = self.generate_search_api_query_parameters(count)
        request = self.http.request('GET', ONEWORLD365_API_URL, fields=query_parameters)

        request_raw_response = request.data.decode("utf-8").strip()
        request_raw_response = request_raw_response[1:-1]

        request_json = json.loads(request_raw_response)
        return request_json

    @staticmethod
    def generate_search_api_query_parameters(search_size):
        return {
            'start': 0,
            'rows': search_size,
            'fq0': 'profile_type:0',
            '0': 0,
            'rf': 1,
        }

    @staticmethod
    def convert_to_standardized_columns(charities):
        return charities

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
