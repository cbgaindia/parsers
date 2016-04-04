'Class for extracting keywords for PDF Documents in a directory'

import csv
import glob,os
import logging
from logging.config import fileConfig
from lxml import etree
import re
import time

DOC_DIR = "union_budgets/2015-16/Expenditure Budget/Volume II/"
OUT_FILE = "union_budgets/2015-16/expenditure_budget_keywords_map.csv"
OUT_CSV_HEADER = ["Department", "Keywords"]
TEMP_INDEX_FILE = "/tmp/page.html"
TEMP_HTML_FILE = "/tmp/pages.html"
LOG_FILE = "/tmp/log"
SKIP_WORDS = ["total", "b. investment in public enterprises", "c. plan outlay", "other programmes", "grand total", "central plan", "state plan", "union territory plans", "union territory plans (with legislature)"]

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()

class KeywordsExtractor(object):
    def __init__(self):
        self.skip_words = SKIP_WORDS
        self.department_name = ""

    def extract_bold_keywords(self):
        '''Extract Bold keywords from all PDF documents in the directory and generate a CSV mapping
        '''
        with open(OUT_FILE, "wb") as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',') 
            csv_writer.writerow(OUT_CSV_HEADER)
            for file_name in glob.glob("%s*.pdf" % DOC_DIR):
                try:
                    self.department_name = os.path.basename(file_name).lower().split(".pdf")[0].decode('utf-8')
                    bold_text_phrases = self.get_bold_text_phrases(file_name)
                    csv_writer.writerow([os.path.basename(file_name).split(".pdf")[0].decode('utf-8'), str(bold_text_phrases)]) 
                    logger.info("Processing PDF document for department: %s" % self.department_name)
                except Exception, error_message:
                    logger.error("Unable to extract keywords for department: %s, error_message: %s" % (self.department_name, error_message))

    def get_bold_text_phrases(self, file_name, is_other_starting_phrases=False, single_word=False, page_num=None, lower_case=True): 
        '''Extract bold text phrases from input HTML object 
        '''
        html_obj = self.get_html_object(file_name, page_num)
        dom_tree = etree.HTML(html_obj.read())
        bold_text_phrases = []
        previous_keyword = None
        for phrase in dom_tree.xpath("//b/text()|//i/text()"):
            phrase = self.clean_extracted_phrase(phrase, is_other_starting_phrases, lower_case)
            if re.search(r'^no. [0-9]+/|^no. [0-9]+|^total-|^total -', phrase) or phrase == self.department_name.encode('utf-8'):
                continue
            if phrase in self.skip_words and not is_other_starting_phrases:
                continue
            if re.search(r'[A-Za-z]{2,}', phrase):
                if not phrase in bold_text_phrases:
                    if not single_word and not len(phrase.split(" ")) > 1:
                        continue
                    bold_text_phrases.append(phrase.strip())
        return bold_text_phrases

    def clean_extracted_phrase(self, phrase, is_other_starting_phrases, lower_case):
        '''Cleanse phrase text to remove unwanted characters and words
        '''
        if lower_case:
            phrase = phrase.lower()
        phrase = phrase.encode('utf-8').replace('\xa0', ' ').replace('\xc2', '').strip()
        phrase = re.sub(r'\s{2,}', ' ', phrase)
        if not is_other_starting_phrases:
            phrase = re.sub(r'[^a-zA-Z\d\)]$', '', phrase)
            phrase = re.sub(r', ETC.$|, etc.$', '', phrase)
            phrase = re.sub(r'^other ', '', phrase).strip()
        return phrase

    def get_html_object(self, file_name, page_num):
        '''Convert PDF file into HTML file using pdftohtml(http://sourceforge.net/projects/pdftohtml/)
        '''
        file_stub = re.sub(r'\s', '_', os.path.basename(file_name).split(".pdf")[0].lower().strip())
        index_file = TEMP_INDEX_FILE.replace(".html", "_%s.html" % file_stub) 
        html_file = TEMP_INDEX_FILE.replace(".html", "_%ss.html" % file_stub) 
        if page_num:
            command = "pdftohtml -f '%s' -l '%s' '%s' '%s' > %s" % (page_num, page_num, file_name, index_file, LOG_FILE)
        else:
            command = "pdftohtml '%s' '%s' > %s" % (file_name, index_file, LOG_FILE)
        os.system(command)
        html_obj = open(html_file, "rb")
        return html_obj

if __name__ == '__main__':
    obj = KeywordsExtractor()
    obj.extract_bold_keywords()
