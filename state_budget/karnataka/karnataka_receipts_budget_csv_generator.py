'CSV generator for Karnataka Receipts Budget PDFs'

import argparse
import logging
from logging.config import fileConfig
from parsers.state_budget.karnataka.karnataka_budget_csv_generator import KarnatakaBudgetCSVGenerator
import re

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()

class KarnatakaReceiptsBudgetCSViGenerator(KarnatakaBudgetCSVGenerator):
    def __init__(self):
        super(KarnatakaReceiptsBudgetCSViGenerator, self).__init__()
        self.min_col_count = 4
        self.max_col_count = 6
        self.parent_scheme_regex = r"([A-Z]+\.|\([a-z]+\)|^[MDCLXVI]+ |^Total)"
        self.voted_charged_column = False

    def extract_head_codes(self, pagewise_table):
        '''Extracting budget codes from scheme descriptions, inheriting classes can customize it
        '''
        for page_num in pagewise_table:
            page_table = pagewise_table[page_num]
            for row_index in range(len(page_table)):
                val = page_table[row_index][0].strip()
                head_code = ""
                head_code_match = re.match(r"^[0-9]{2,}\s", val)
                if head_code_match:
                    head_code = head_code_match.group(0)
                page_table[row_index][0] = head_code.strip()
                page_table[row_index].insert(1, val.replace(head_code, ""))
        return pagewise_table

    def extract_budget_codes(self, pagewise_table):
        '''Extracting Budget codes from scheme descriptions, inheriting classes can customize it
        '''
        for page_num in pagewise_table:
            page_table = pagewise_table[page_num]
            for row_index in range(1, len(page_table)):
                val = page_table[row_index][1].strip()
                budget_code = ""
                budget_code_match = re.findall(r"([0-9\-]{2,}\-[0-9]{2,})+", val)
                if budget_code_match:
                    budget_code = budget_code_match[0]
                page_table[row_index][1] = budget_code.strip()
                page_table[row_index].insert(2, val.replace(budget_code, ""))
        return pagewise_table

    def clean_header_values(self, row_index, page_table):
        '''CLeaning and generating correct header values and unwanted row indices
        '''
        unwanted_row_indices = {}
        if re.match(r"[0-9]{4}\-[0-9]{2}", page_table[row_index][2]):
            page_table[row_index][0] = "Head Code"
            for col_index in range(1, len(page_table[row_index])):
                header_val = ""
                for index in range(row_index+1):
                    header_val += " " + page_table[index][col_index].strip()
                    if index != row_index:
                        unwanted_row_indices[index] = True
                if col_index > 1:
                    header_val =  header_val + " " + self.currency_slug
                page_table[row_index][col_index] = header_val.strip()
            page_table[row_index].insert(1,"Budget Code")
        return unwanted_row_indices.keys()


    def generate_page_headers_map(self, pagewise_table):
        '''Generating pagewise headers for tables
        '''
        pagewise_keywords = {}
        page_headers_map = {}
        for page_num in pagewise_table:
            keyword_list = self.keywords_extractor.get_bold_text_phrases(self.input_file, keyword_xpath="//text()", is_other_starting_phrases=True, single_word=True, page_num=page_num, lower_case=False)
            page_header = []
            for keyword in keyword_list:
                keyword = re.sub(self.empty_char_regex, '', keyword).replace('\x90', '-')
                if " ".join(self.currency_slug.split(" ")[1:]) in keyword or "Lakhs" in keyword:
                    break
                if not "<!--" in keyword:
                    keyword = keyword.decode('unicode_escape').encode('ascii','ignore').strip()
                    keyword = re.sub(r"-\s|--", " ",  keyword)
                    keyword = re.sub(r"\s{2,}", " ", keyword)
                    page_header.append(keyword.strip())
            page_headers_map[page_num] = "|".join(page_header)
        return page_headers_map


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files from Karnataka Receipts State Budget PDF Document")
    parser.add_argument("input_file", help="Input filepath for budget document")
    parser.add_argument("output_dir", help="Output directory for budget document")
    args = parser.parse_args()
    obj = KarnatakaReceiptsBudgetCSViGenerator()
    if not args.input_file or not args.output_dir:
        print("Please input directory to begin CSV extraction")
    else:
        obj.generate_karnataka_budget_csv(args.input_file, args.output_dir)
