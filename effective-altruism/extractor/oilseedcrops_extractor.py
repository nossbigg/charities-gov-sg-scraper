import csv
import json
import re

from PyPDF2 import PdfFileReader

# original source:
# http://www.oilseedcrops.org/wp-content/uploads/2013/07/Myanmar-Local-NGO-directory-2012.pdf
OILSEEDCROPS_PDF_PATH = '../data/Myanmar-Local-NGO-directory-2012.pdf'

CHARITIES_JSON_DUMP_PATH = '../data/oilseedcrops.json'
CHARITIES_CSV_DUMP_PATH = '../data/oilseedcrops.csv'


class OilSeedCropsExtractor:
    def do_extract(self):
        pdf = PdfFileReader(open(OILSEEDCROPS_PDF_PATH, "rb"))

        organization_entities = self.get_organizations_from_index_pages(pdf)
        for organization_name, organization in organization_entities.items():
            organization['raw_text'] = self.get_organization_raw_text(pdf, organization)
        for organization_name, organization in organization_entities.items():
            organization.update(self.get_organization_details(organization))

        charities_columns_standardized \
            = self.convert_to_standardized_columns(list(organization_entities.values()))

        self.write_list_as_json_to_file(
            CHARITIES_JSON_DUMP_PATH, charities_columns_standardized)
        self.write_list_as_csv_to_file(
            CHARITIES_CSV_DUMP_PATH, charities_columns_standardized)

        pass

    @staticmethod
    def get_organization_details(organization):
        organization_raw_text_list = organization['raw_text']
        organization_name = organization['name']

        background_matcher \
            = re.compile(r"(?<=Background)(.+?)(?=Vision/Mission)")
        vision_mission_matcher \
            = re.compile(r"(?<=Vision/Mission)(.+?)(?=Main Activities)")
        main_activities_matcher \
            = re.compile(r"(?<=Main Activities)(.+?)(?=Primary BeneÞ  ciaries)")
        primary_beneficiaries_matcher \
            = re.compile(r"(?<=Primary BeneÞ  ciaries)(.+?)(?=Name of Leader)")

        organization_name_special_escaped = re.sub("\(.+?\)", "", organization_name).strip()
        organization_info_matcher \
            = re.compile(organization_name_special_escaped + "(.+?)(?=Name of Leader)")

        organization_full_text = ""
        for text in organization_raw_text_list:
            organization_full_text = organization_full_text + " " + text
        organization_full_text = organization_full_text.replace("\n", " ")

        organization_info = organization_info_matcher.search(organization_full_text)
        if organization_info is not None:
            organization_full_text = organization_full_text.replace(organization_info.group(0), " ")

        background_info = background_matcher.search(organization_full_text)
        vision_mission_info = vision_mission_matcher.search(organization_full_text)
        main_activities_info = main_activities_matcher.search(organization_full_text)
        primary_beneficiaries_info \
            = primary_beneficiaries_matcher.search(organization_full_text)

        def get_matcher_result_or_blank(match):
            if match is None:
                return ""

            matched_text = match.group(0)
            return matched_text.strip()

        return {
            'organization_info': get_matcher_result_or_blank(organization_info),
            'background': get_matcher_result_or_blank(background_info),
            'vision_mission': get_matcher_result_or_blank(vision_mission_info),
            'main_activities': get_matcher_result_or_blank(main_activities_info),
            'primary_beneficiaries': get_matcher_result_or_blank(primary_beneficiaries_info),
            'country': 'myanmar'
        }

    @staticmethod
    def get_organization_raw_text(pdf, organization):
        organization_page_numbers = range(organization['start_page'], organization['end_page'] + 1)
        organization_unmerged_raw_text = \
            [pdf.getPage(number).extractText() for number in organization_page_numbers]

        return organization_unmerged_raw_text

    @staticmethod
    def get_organizations_from_index_pages(pdf):
        PAGE_OFFSET = 3

        index_pages = [pdf.getPage(1), pdf.getPage(2), pdf.getPage(3)]

        index_pages_raw_text = ""
        for page in index_pages:
            index_pages_raw_text = index_pages_raw_text + "\n" + page.extractText()
        index_pages_raw_text = index_pages_raw_text.replace("\n\n", "\n")

        def collapse_page_numbers(raw_text):
            collapse_page_numbers_matcher = re.compile(r"\n[ ]*?[0-9]+?-?[0-9]*?\n")

            cleaned_text = raw_text
            for matched_page_number in collapse_page_numbers_matcher.findall(raw_text):
                cleaned_text = cleaned_text.replace(matched_page_number,
                                                    matched_page_number.strip() + "\n")

            return cleaned_text

        index_pages_collapsed_page_numbers = collapse_page_numbers(index_pages_raw_text)

        organization_entry_matcher = re.compile(r"^\d*?\..*$", re.MULTILINE)
        organization_entries_uncleaned = \
            [line for line in index_pages_collapsed_page_numbers.split("\n")
             if organization_entry_matcher.match(line)]

        def get_organization(raw_organization_line):
            organization_line_matcher \
                = re.compile(r"^[0-9]+?. (.*?)[ ]*?([0-9]+-?[0-9]*).*?$")
            matcher = organization_line_matcher.match(raw_organization_line)

            pages_component = matcher.group(2)
            if "-" in pages_component:
                start_page = pages_component.split("-")[0]
                end_page = pages_component.split("-")[1]
            else:
                start_page = pages_component
                end_page = pages_component

            return {
                'name': matcher.group(1).strip(),
                'start_page': PAGE_OFFSET + int(start_page),
                'end_page': PAGE_OFFSET + int(end_page),
            }

        organizations_list = \
            [get_organization(name) for name in organization_entries_uncleaned]
        organizations = {value['name']: value for value in organizations_list}
        return organizations

    @staticmethod
    def convert_to_standardized_columns(charities):
        columns_to_remove = ["start_page", "end_page", "raw_text"]

        for charity in charities:
            charity['description'] = \
                charity.pop('background') + " " + \
                charity.pop('vision_mission') + " " + \
                charity.pop('main_activities') + " " + \
                charity.pop('primary_beneficiaries')
            charity['address'] = charity.pop('organization_info')

            for column_name_to_remove in columns_to_remove:
                del charity[column_name_to_remove]

        return charities

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


OilSeedCropsExtractor().do_extract()
