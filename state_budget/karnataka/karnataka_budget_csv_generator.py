'CSV generator for Karnataka Budget PDFs'

import argparse
import csv
import logging
from logging.config import fileConfig
import re
import os
from parsers.pdf_to_csv import PDF2CSV
from parsers.keywords_extractor import KeywordsExtractor
fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()


class KarnatakaBudgetCSVGenerator(PDF2CSV):
    def __init__(self):
        super(KarnatakaBudgetCSVGenerator, self).__init__()
        self.keywords_extractor = KeywordsExtractor()
        self.min_col_count = 8
        self.max_col_count = 10
        self.currency_slug = "(Rs. in Lakhs)"
        self.empty_char_regex = r'(\xe2|\xc3|\x82|\xa2|\x80)'
        self.parent_scheme_regex = r"([A-Z]+\.|\([a-z]+\)|\d{4,}|^[MDCLXVI]+ |^Total)"
        self.voted_charged_column = True

    def generate_karnataka_budget_csv(self, input_file, output_dir):
        '''
        Main call comes here setting global variable and calling PDF to CSV
        '''
        self.input_file = input_file
        self.output_dir = output_dir
        self.generate_csv_file(input_file, input_file.split(".pdf")[0] + ".csv",
                               is_header=True, identify_columns=True)

    def modify_table_data(self, table):
        '''
        Modifying output of PDF to CSV to clean, wrangle and generate multiple CSV files
        '''
        pagewise_table = self.split_pages(table)
        pagewise_table = self.extract_head_codes(pagewise_table)
        pagewise_table = self.clean_pagewise_table(pagewise_table)
        for page_num in pagewise_table:
            unwanted_row_indices = []
            page_table = pagewise_table[page_num]
            header_found = False
            for row_index in range(len(page_table)):
                self.correct_column_count(row_index, page_table)
                unwanted_header_row_indices = self.clean_header_values(row_index,
                                                                       page_table)
                if unwanted_header_row_indices:
                    unwanted_row_indices += unwanted_header_row_indices
                    header_found = True
                elif header_found and self.voted_charged_column:
                    page_table[row_index].insert(2, "")
                self.correct_combined_values(row_index, page_table)
            unwanted_row_indices += self.merge_splitted_rows(page_table)
            self.delete_unwanted_rows(unwanted_row_indices, page_table)
        pagewise_headers = self.generate_page_headers_map(pagewise_table)
        pagewise_table = self.extract_budget_codes(pagewise_table)
        self.generate_pagewise_csv_files(pagewise_table, pagewise_headers)

    def split_pages(self, table):
        '''
        Splitting main table into pagewise tables
        '''
        pagewise_table = {}
        temp_list = []
        page_num = 1
        for row in table:
            if row[0] == self.page_break.replace('"', ''):
                if temp_list and len(temp_list[0]) > self.min_col_count:
                    pagewise_table[page_num] = temp_list
                    temp_list = []
                page_num += 1
            elif len(row) > self.min_col_count:
                temp_list.append(row)
        if temp_list and len(temp_list[0]) > self.min_col_count:
            pagewise_table[page_num] = temp_list
        return pagewise_table

    def extract_head_codes(self, pagewise_table):
        '''
        Extracting Head codes from scheme descriptions, inheriting classes can customize it
        '''
        return pagewise_table

    def extract_budget_codes(self, pagewise_table):
        '''
        Extracting Budget codes from scheme descriptions, inheriting classes can customize it
        '''
        return pagewise_table

    def clean_pagewise_table(self, pagewise_table):
        '''
        Cleansing pagewise tables to remove Kannada chars(Windows-1252 encoded)
        '''
        for page_num in pagewise_table:
            page_table = pagewise_table[page_num]
            unwanted_row_indices = {}
            for row_index in range(len(page_table)):
                for col_index in range(len(page_table[row_index])):
                    val = page_table[row_index][col_index]
                    val = re.sub(r'(\xe2|\x80|vjU)', '', val).replace('\x90', '-')
                    if '\\x' in val.encode('string-escape'):
                        if " " in val:
                            val = re.sub(r"\s{2,}", " ", val)
                            val_list = val.split(" ")
                            clear_index = 0
                            for val_index in range(len(val_list)):
                                if not '\\x' in val_list[val_index].encode('string-escape') and re.findall(r"[a-zA-Z0-9\.\(\)\&\-\+]{1,}", val_list[val_index]):
                                    if clear_index == 0:
                                        clear_index = val_index
                                else:
                                    clear_index = 0
                            if clear_index > 0:
                                val =  " ".join(val.split(" ")[clear_index:])
                            else:
                                val = ""
                        else:
                            val = ""
                    page_table[row_index][col_index] = val.strip()
                if not "".join(page_table[row_index]).strip():
                    unwanted_row_indices[row_index] = True
            self.delete_unwanted_rows(unwanted_row_indices.keys(), page_table)
        return pagewise_table

    def correct_column_count(self,row_index, page_table):
        '''Inserting extra columns wherever required
        '''
        while len(page_table[row_index]) < self.max_col_count:
            page_table[row_index].insert(0, "")

    def correct_combined_values(self, row_index, page_table):
        '''Correcting Grand Total and Voted/Charged values which got merged in original doc
        '''
        if page_table[row_index][1] == "GRAND TOTAL (PLAN + NON-PLAN)":
            col_index = 2
            while col_index < len(page_table[row_index]):
                if not "." in page_table[row_index][col_index]:
                    page_table[row_index][col_index+1] = page_table[row_index][col_index] + page_table[row_index][col_index+1]
                    page_table[row_index][col_index] = "P+NP ="
                col_index += 2
        voted_charged_match = re.findall(r"(\s){,1}(Voted|Charged)$", page_table[row_index][1])
        if voted_charged_match:
            voted_charged_match = "".join(map(list, voted_charged_match)[0])
            page_table[row_index][1] = page_table[row_index][1].split(voted_charged_match)[0]
            page_table[row_index][2] = voted_charged_match.strip()

    def clean_header_values(self, row_index, page_table):
        '''CLeaning and generating correct header values and unwanted row indices
        '''
        unwanted_row_indices = []
        if page_table[row_index][2] == "Plan":
            page_table[row_index][0] = "Budget Code"
            header_1_val = ""
            for index in range(row_index+1):
                header_1_val += " " + page_table[index][1]
                if index != row_index:
                    unwanted_row_indices.append(index)
            page_table[row_index][1] = header_1_val.strip()
            year_index = 2
            for col_index in range(2, len(page_table[row_index])):
                if col_index%2 == 0 and col_index != year_index:
                    year_index += 2
                if not " " in page_table[0][year_index+1]:
                    page_table[0][year_index+1] = " " + page_table[0][year_index+1]
                page_table[row_index][col_index] = page_table[0][year_index] + page_table[0][year_index+1] + " " + page_table[row_index][col_index] + " " + self.currency_slug
            page_table[row_index].insert(2, 'Voted/Charged')
        elif page_table[row_index][2] == "2":
            unwanted_row_indices.append(row_index)
        return unwanted_row_indices

    def merge_splitted_rows(self, page_table):
        '''Merging splitted rows into one
        '''
        unwanted_row_indices = {}
        for row_index in range(5, len(page_table)):
            if re.match(self.parent_scheme_regex, page_table[row_index][1]) or page_table[row_index][0]:
                continue
            elif not "".join(page_table[row_index][2:]):
                parent_row_index = row_index
                while not (re.match(self.parent_scheme_regex, page_table[parent_row_index][1]) or page_table[parent_row_index][0]):
                    parent_row_index -= 1
                    if parent_row_index in unwanted_row_indices:
                        continue
                    if page_table[row_index][1].strip():
                        if len(page_table) < abs(parent_row_index):
                            page_table[parent_row_index][1] += ' ' + page_table[row_index][1].strip()
                    unwanted_row_indices[row_index] = True
        return unwanted_row_indices.keys()

    def delete_unwanted_rows(self, unwanted_row_indices, page_table):
        '''Deleting unwanted row indices from page tables
        '''
        unwanted_row_indices.sort()
        num = 0
        for row_index in unwanted_row_indices:
            page_table.pop(row_index-num)
            num += 1

    def generate_page_headers_map(self, pagewise_table):
        '''Generating pagewise headers for tables
        '''
        page_headers_map = {}
        for page_num in pagewise_table:
            keyword_list = self.keywords_extractor.get_bold_text_phrases(self.input_file, keyword_xpath="//text()", is_other_starting_phrases=True, single_word=True, page_num=page_num, lower_case=False)
            page_header = []
            for keyword_index in range(len(keyword_list)):
                keyword = keyword_list[keyword_index]
                keyword = re.sub(self.empty_char_regex, '', keyword).replace('\x90', '-')
                if not '\\x' in keyword.encode('string-escape') and not "<!--" in keyword:
                    if " ".join(self.currency_slug.split(" ")[1:]) in keyword or "in Lakhs" in keyword:
                        break
                    keyword = keyword.decode('unicode_escape').encode('ascii','ignore').strip()
                    keyword = re.sub(r"\s{2,}", " ", keyword)
                    if "VOLUME" in keyword and keyword_index > 0:
                        keyword = keyword + keyword_list[keyword_index-1].split(":")[-1]
                    page_header.append(keyword.strip())
            page_headers_map[page_num] = "|".join(page_header[:3])
        return page_headers_map

    def write_page_table(self, file_name, file_table):
        '''Creating new file and writing file table in it
        '''
        file_name = file_name.split("|")[2].strip() + "|" + file_name.split("|")[1].strip()
        file_name = file_name.replace("/", "|")
        out_csv_file = open(self.output_dir + "/" + file_name + ".csv", "wb")
        csv_writer = csv.writer(out_csv_file, delimiter=',')
        for row in file_table:
            csv_writer.writerow(row)
        out_csv_file.close()

    def generate_pagewise_csv_files(self, pagewise_table, pagewise_headers):
        '''Generating pagewise CSV files
        '''
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        file_name = ""
        file_table = []
        for page_num in pagewise_table:
            if file_name and file_name != pagewise_headers[page_num]:
                self.write_page_table(file_name, file_table)
                file_table = pagewise_table[page_num]
                file_name = pagewise_headers[page_num]
            else:
                if not file_name:
                    file_table += pagewise_table[page_num]
                elif len(pagewise_table[page_num]) <= 1:
                    continue
                else:
                    if re.match(self.parent_scheme_regex, pagewise_table[page_num][1][1]) or pagewise_table[page_num][1][0]:
                        file_table += pagewise_table[page_num][1:]
                    elif not "".join(pagewise_table[page_num][1][2:]):
                        file_table[-1][1] += " " + pagewise_table[page_num][1][1]
                        file_table += pagewise_table[page_num][2:]
                file_name = pagewise_headers[page_num]
        if file_table:
            self.write_page_table(file_name, file_table)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files from Karnataka State Budget PDF Document")
    parser.add_argument("input_file", help="Input filepath for budget document")
    parser.add_argument("output_dir", help="Output directory for budget document")
    args = parser.parse_args()
    obj = KarnatakaBudgetCSVGenerator()
    if not args.input_file or not args.output_dir:
        print("Please input directory to begin CSV extraction")
    else:
        obj.generate_karnataka_budget_csv(args.input_file, args.output_dir)
