import csv
import itertools
import json
import re
from string import Template

import urllib3
from bs4 import BeautifulSoup

EPIC_FOUNDATION_CHARITIES_URL = \
    'https://epic.foundation/inside-epic/portfolio-organizations'

EPIC_FOUNDATION_CSV_DUMP_PATH = '../data/epicfoundation.csv'
EPIC_FOUNDATION_JSON_DUMP_PATH = '../data/epicfoundation.json'


class EpicFoundationExtractor:
    http = urllib3.PoolManager()

    def do_scrape(self):
        charities = self.get_charities()
        charities_with_details = self.get_charities_detailed(charities)

        charities_column_names_standardized = self.convert_to_standardized_columns(
            charities_with_details)

        self.write_list_as_json_to_file(EPIC_FOUNDATION_JSON_DUMP_PATH,
                                        charities_column_names_standardized)
        self.write_list_as_csv_to_file(EPIC_FOUNDATION_CSV_DUMP_PATH,
                                       charities_column_names_standardized)

    def get_charities(self):
        request = self.http.request('GET', EPIC_FOUNDATION_CHARITIES_URL)
        request_html_body = request.data.decode("UTF-8")

        soup = BeautifulSoup(request_html_body, 'html.parser')

        charities_container = soup.find("div", class_="org-browser")
        if charities_container is None:
            return []

        charities_elements = charities_container.find_all("div", recursive=False)
        charities = [{"data-link": charity_div['data-link']} for charity_div in charities_elements]

        return charities

    def get_charities_detailed(self, charities):
        return [{**charity, **self.get_charity_detailed_page(charity)}
                for charity in charities]

    def get_charity_detailed_page(self, charity):
        charity_data_link = charity['data-link']
        charity_detailed_page_url = self.generate_charity_details_url(charity_data_link)

        request = self.http.request('GET', charity_detailed_page_url)
        request_html_body = request.data.decode("UTF-8")

        return self.get_charity_details_from_page_html(request_html_body)

    def get_charity_details_from_page_html(self, request_html_body):
        soup = BeautifulSoup(request_html_body, 'html.parser')

        charity_details = {
            'org-name': soup.find('h2', class_="org-name").text,
            **self.get_country_and_location(soup),
            **self.get_quote(soup),
            **self.get_intro(soup),
            **self.get_challenges(soup),
            **self.get_key_facts(soup),
            **self.get_key_programs(soup),
        }

        return charity_details

    def convert_to_standardized_columns(self, charities):
        columns_to_keep = ["location", "country", "name", "cause_area", "description"]

        for charity in charities:
            charity['location'] = charity.get('org-location', '')
            charity['country'] = charity.get('org-country', '')
            charity['name'] = charity.get('org-name', '')
            charity['cause_area'] = charity.get('fact-Sectors', '')

            challenge_descriptions = charity.get('challenge-description', ' ')
            challenge_description \
                = self.convert_challenge_descriptions_to_string(challenge_descriptions)

            charity['description'] \
                = charity.get('org-intro', ' ') + "; " \
                  + charity.get('org-quote', ' ') + "; " \
                  + challenge_description

            for column_name in list(charity.keys()):
                if column_name not in columns_to_keep:
                    del charity[column_name]

        return charities

    @staticmethod
    def get_country_and_location(soup):
        location_element = soup.find("span", {"lang": "en"}, class_="org-location")
        country_element = soup.find("span", {"lang": "en"}, class_="org-country")

        return {
            "org-location": location_element.text,
            "org-country": country_element.text,
        }

    @staticmethod
    def get_quote(soup):
        org_presentation_element = soup.find("div", class_="org-presentation")
        if org_presentation_element is None:
            return {}

        quote_element = org_presentation_element.find('span', {"lang": "en"})
        quote = quote_element.text
        quote = re.sub("[\r\n]", " ", quote)
        return {'org-quote': quote}

    @staticmethod
    def get_intro(soup):
        org_intro_element = soup.find("div", class_="org-intro")
        if org_intro_element is None:
            return {}

        p_elements = org_intro_element.find_all('p', {"lang": "en"})
        org_intro = " ".join([p.string for p in p_elements])
        org_intro = re.sub("[\r\n]", " ", org_intro)

        return {'org-intro': org_intro}

    @staticmethod
    def get_challenges(soup):
        challenge_element = soup.find("div", class_="challenge-description")
        if challenge_element is None:
            return {}

        facts = []

        fact_elements = challenge_element.find_all('div', recursive=False)
        for fact_element in fact_elements:
            spans = fact_element.find_all('span', {"lang": "en"})
            fact_string = ", ".join([span.text for span in spans
                                     if len(span.text) > 0])
            facts.append(fact_string)

        facts_string = "; ".join(facts)
        facts_string = re.sub("[\r\n]", " ", facts_string)

        return {'challenge-description': facts_string}

    @staticmethod
    def get_key_facts(soup):
        key_facts_container_element = soup.find("div", class_="org-details")
        if key_facts_container_element is None:
            return {}

        facts = {}

        fact_elements = key_facts_container_element.find_all('div', recursive=False)
        for fact_element in fact_elements:
            spans = fact_element.find_all('span', {"lang": "en"})

            if len(spans) != 2:
                fact_field = 'fact-unknown'
                value = spans[0].text
                facts[fact_field] = value
                continue

            fact_field = "fact-" + spans[0].text
            fact_value = spans[1].text
            facts[fact_field] = fact_value

        return facts

    @staticmethod
    def get_key_programs(soup):
        programs_container_element = soup.find("div", class_="org-programs-description-wrapper")
        if programs_container_element is None:
            return {}

        programs = []

        program_elements = programs_container_element.find_all(
            'div', class_="org-programs-description", recursive=False)
        for program_element in program_elements:
            program_header_element = program_element.find('span', {"lang": "en"})
            program_header_text = program_header_element.text \
                if program_header_element is not None \
                else ""

            paragraphs = program_element.find_all('p', {"lang": "en"})
            program_text = " ".join([p.text for p in paragraphs
                                     if len(p.text) > 0])
            program_text = re.sub("[\r\n]", " ", program_text)

            programs.append({program_header_text: program_text})

        return {'challenge-description': programs}

    @staticmethod
    def convert_challenge_descriptions_to_string(challenge_descriptions):
        challenge_descriptions_flattened = []

        for challenge in challenge_descriptions:
            for challenge_title in challenge.keys():
                challenge_content = challenge[challenge_title]
                challenge_descriptions_flattened.append(challenge_title + ": " + challenge_content)

        return "; ".join(challenge_descriptions_flattened)

    @staticmethod
    def generate_charity_details_url(data_link):
        charity_details_url_template = Template(
            'https://epic.foundation/inside-epic/portfolio/$data_link')
        return charity_details_url_template.substitute(data_link=data_link)

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
