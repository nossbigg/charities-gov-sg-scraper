import csv
import itertools
import json

import urllib3

CAFA_API_URL = \
    'https://cafa.iphiview.com/cafa/API/EnhancedCharitySearch/' \
    'dagenhancedcharitysearchbyfocusandgeographicarea'

CAFA_JSON_DUMP_PATH = '../data/cafa.json'
CAFA_CSV_DUMP_PATH = '../data/cafa.csv'


class CafaExtractor:
    http = urllib3.PoolManager()

    def do_scrape(self):
        number_of_charities = self.get_number_of_charities()

        charities_unflattened = \
            [self.get_charities_page(start_index)
             for start_index in range(0, number_of_charities, 10)]

        charities = list(itertools.chain.from_iterable(charities_unflattened))

        charities_column_names_standardized = self.convert_to_standardized_columns(charities)

        self.write_list_as_json_to_file(CAFA_JSON_DUMP_PATH, charities_column_names_standardized)
        self.write_list_as_csv_to_file(CAFA_CSV_DUMP_PATH, charities_column_names_standardized)

    def get_number_of_charities(self):
        query_parameters = self.generate_default_query_parameters()
        request = self.http.request('POST', CAFA_API_URL, fields=query_parameters)
        request_json = json.loads(request.data)
        return request_json['Count']

    def get_charities_page(self, start_index):
        query_parameters = self.generate_default_query_parameters()
        query_parameters['startIndex'] = start_index
        request = self.http.request('POST', CAFA_API_URL, fields=query_parameters)
        request_json = json.loads(request.data)
        return request_json['Data']

    @staticmethod
    def convert_to_standardized_columns(charities):
        columns_to_remove = ["Id", "Nickname", "DetailsDispatch", "DagDispatch", "GrantDispatch"]

        for charity in charities:
            charity['name'] = charity.pop('Name')
            charity['cause_area'] = charity.pop('FieldsOfInterest')

            for column_name_to_remove in columns_to_remove:
                del charity[column_name_to_remove]

        return charities

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
    def write_list_as_json_to_file(filepath, list_of_dicts):
        with open(filepath, 'w') as file_out:
            json.dump(list_of_dicts, file_out)

    @staticmethod
    def write_list_as_csv_to_file(filepath, list_of_dicts):
        with open(filepath, mode='w', newline="\n") as csv_file:
            fieldnames = list_of_dicts[0].keys()
            csv_file_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            csv_file_writer.writeheader()
            for charity in list_of_dicts:
                csv_file_writer.writerow(charity)
