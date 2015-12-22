'CSV generator for Combined Budget IPFS PDFs'

import argparse
import csv
import glob
import logging
from logging.config import fileConfig
import re
import os
from parsers.pdf_to_csv import PDF2CSV
from parsers.keywords_extractor import KeywordsExtractor

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()
MIN_COL_COUNT = 5

class CombinedBudgetCSVGenerator(PDF2CSV):
    def __init__(self):
        super(CombinedBudgetCSVGenerator, self).__init__()
        self.keywords_extractor = KeywordsExtractor()        
        self.input_file = None
        self.output_dir = None
        self.currency_handle = '(` crore)'
        self.separator = " || " 
        self.continued_symbol = "(CONTD"

    def generate_combined_budget_csv(self, input_file, output_dir):
        self.input_file = input_file
        self.output_dir = output_dir
        self.generate_csv_file(input_file, input_file.split(".pdf")[0] + ".csv", is_header=False)

    def modify_table_data(self, table):
        pagewise_table = self.split_pages(table)
        pagewise_table = self.clean_pagewise_table(pagewise_table)
        pagewise_table,pagewise_keywords = self.create_page_to_file_map(pagewise_table)
        self.generate_child_csv_files(pagewise_table, pagewise_keywords)
        return None

    def split_pages(self, table):
        pagewise_table = {}
        temp_list = []
        page_num = 1
        for row in table:
            if row[0] == self.page_break.replace('"',''):
                if temp_list and len(temp_list[0]) > MIN_COL_COUNT:
                    pagewise_table[page_num] = temp_list
                    temp_list = []
                page_num += 1
            elif len(row) > MIN_COL_COUNT:
                temp_list.append(row)
        if temp_list and len(temp_list[0]) > MIN_COL_COUNT:
            pagewise_table[page_num] = temp_list
        return pagewise_table

    def clean_pagewise_table(self, pagewise_table):
        for page_num in pagewise_table:
            page_table = pagewise_table[page_num]
            for row_index in range(len(page_table)):
                for col_index in range(len(page_table[row_index])):
                    page_table[row_index][col_index] = page_table[row_index][col_index].strip() 
            while page_table[0][0].strip() == page_table[0][1].strip() == "":
                for row in page_table:
                    row[0] = (row[0] + " " + row[1]).strip()
                    row.pop(1)
            empty_row_indices = []
            for row_index in range(len(page_table)):
                if not "".join(page_table[row_index][1:]).strip():
                    page_table[row_index-1][0] = page_table[row_index-1][0] + " " + page_table[row_index][0]
                    empty_row_indices.append(row_index)
            num = 0
            for row_count in empty_row_indices:
                page_table.pop(row_count-num)
                num += 1
            pagewise_table[page_num] = page_table 
        return pagewise_table

    def create_page_to_file_map(self, pagewise_table): 
        pagewise_keywords = {}
        for page_num in pagewise_table:
            pagewise_keywords[page_num] = self.keywords_extractor.get_bold_text_phrases(self.input_file, is_other_starting_phrases=True, single_word=True, page_num=page_num, lower_case=False)
        for page_num in pagewise_keywords:
            currency_handle_found = False
            for keyword_index in range(len(pagewise_keywords[page_num])):
                if pagewise_keywords[page_num][keyword_index] == self.currency_handle:
                    currency_handle_found = True
                    pagewise_keywords[page_num] = self.separator.join(pagewise_keywords[page_num][0:keyword_index])
                    break
            if not currency_handle_found:
                pagewise_keywords[page_num] = pagewise_keywords[page_num][0]
            if self.continued_symbol in pagewise_keywords[page_num]:
                if not self.separator in pagewise_keywords[page_num]:
                    pagewise_keywords[page_num] = pagewise_keywords[page_num-1] 
                    pagewise_table[page_num] = pagewise_table[page_num-1] + pagewise_table[page_num]
                    pagewise_table.pop(page_num-1)
                else:
                    pagewise_keywords[page_num] = pagewise_keywords[page_num-1].split(self.separator)[0] + self.separator + pagewise_keywords[page_num].split(self.separator)[-1] 
        return pagewise_table,pagewise_keywords

    def generate_child_csv_files(self, pagewise_table, pagewise_keywords):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        for page_num in pagewise_table:
            file_name = re.sub(r'^TABLE ', '', pagewise_keywords[page_num]).strip()
            file_name = file_name.replace("/", '|')
            file_name = file_name.replace(self.separator, '-')
            out_csv_file = open(self.output_dir + "/" + file_name + ".csv", "wb")
            csv_writer = csv.writer(out_csv_file, delimiter=',')
            for row in pagewise_table[page_num]:
                csv_writer.writerow(row)
            out_csv_file.close() 
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files from Combined Budget PDF Document(IPFS)")
    parser.add_argument("input_file", help="Input filepath for budget document")
    parser.add_argument("output_dir", help="Output filepath for budget document")
    args = parser.parse_args()
    obj = CombinedBudgetCSVGenerator()
    if not args.input_file or not args.output_dir: 
        print("Please input directory to begin CSV extraction")
    else:
        obj.generate_combined_budget_csv(args.input_file, args.output_dir)
