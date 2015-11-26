'CSV generator for Expenditure Budget PDFs'

import argparse
import glob
import logging
from logging.config import fileConfig
import re
import os
from parsers.pdf_to_csv import PDF2CSV

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()

SKIP_FILENAMES = ["all statements of budget estimates"]
SECOND_HEADER_FIELD = "budget support"

class ExpenditureBudgetCSVGenerator(PDF2CSV):
    def __init__(self):
        self.header_rows_indices = [0,1,2]
        self.header_rows_cap = 5

    def modify_table_data(self, table):
        table = self.merge_splitted_coloumns(table)
        table = self.remove_dulicate_headers(table)
        table = self.fix_second_header(table)
        empty_row_indices = []
        for row_num in range(len(table)-1):
            if table[row_num][1].strip() == "Major" and table[row_num+1][1].strip() == "Head":
                table[row_num+1][1] = table[row_num][1] + table[row_num+1][1] 
                table[row_num][1] == ""
                empty_row_indices.append(row_num)
        for row_count in empty_row_indices:
            table.pop(row_count)
        table = self.split_merged_coloumns(table)
        table = self.merge_splitted_rows(table)
        table = self.add_index_coloumn(table)
        table = self.add_new_headers(table)
        return table

    def merge_splitted_coloumns(self, table):
        if table[1][0] == table[1][1] == "":
            for row in table:
                row[0] += row[1]
                row.pop(1)
        return table
    
    def split_merged_coloumns(self, table):
        for row in table:
            for col_index in range(1,len(row)):
                if re.search(r'\.{3}\s(\.{3}|[0-9]|\-[0-9])', row[col_index]) and not row[col_index-1].strip():
                    row[col_index-1] = "..."
                    row[col_index] = re.sub(r'^\.{3}\s', '', row[col_index]).strip()
        new_col_indices = []
        for row_index in range(len(table)):
            row = table[row_index]
            new_col_values_map = {}
            for col_index in range(1, len(row)):
                if re.search(r'(\.{3}|[0-9]|\-[0-9]|Plan|Non-Plan|IEBR)\s(\.{3}|[0-9]|\-[0-9]|Non-Plan|Total)', row[col_index]):
                    col_values = row[col_index].strip().split(" ")
                    row[col_index] = col_values[0]
                    for col_count in range(1,len(col_values)):
                        if col_index+col_count < len(row) and not row[col_index+col_count].strip():
                            row[col_index+col_count] = col_values[col_count]
                        else:
                            new_col_values_map[col_index+col_count] = col_values[col_count] 
                            if not col_index+col_count in new_col_indices and row_index <= self.header_rows_cap:
                                new_col_indices.append(col_index+col_count)
            num = 0
            for index in sorted(new_col_values_map):
                row.insert(index+num, new_col_values_map[index])
                num += 1
        table = self.correct_major_head_values(table)
        for col_index in new_col_indices:
            table[0].insert(col_index, " ")
        return table
       
    def correct_major_head_values(self, table):
        for row in table:
            major_code_match = re.search(r'\D{2,}\s[0-9]{4,}$', row[0].strip())
            if major_code_match:
                major_code = major_code_match.group(0).split(" ")[-1].strip()
                scheme_name = row[0].split(major_code)[0]
                row[0] = scheme_name.strip()
                if not row[1].strip():
                    row[1] = major_code
                else:
                    row.insert(1, major_code)
        for row in table:
            major_head_val = row[1].strip() 
            if major_head_val and re.search(r'(^[0-9]{1,}\.[0-9]{1,})|\.{3}', major_head_val):
                row.insert(1, '')
        return table
    
    def remove_dulicate_headers(self, table):
        empty_row_indices = []
        header_rows = []
        for row_num in self.header_rows_indices:
            header_rows.append("".join(table[row_num]).strip())
        for row_num in range(self.header_rows_indices[-1]+1, len(table)):
            if "".join(table[row_num]).strip() in header_rows:
                empty_row_indices.append(row_num)
        num = 0
        for row_count in empty_row_indices:
            table.pop(row_count-num)
            num += 1
        return table

    def merge_splitted_rows(self, table):
        empty_row_indices = []
        for row_index in range(1,len(table)):
            if re.search(r'^([0-9]|Total)', table[row_index][0]):
                continue
            if table[row_index][0].strip() and not "".join(table[row_index][1:]).strip() and table[row_index-1][0].strip():
                parent_row_index = row_index
                while parent_row_index > 1:
                    parent_row_index -= 1
                    if "".join(table[parent_row_index][1:]).strip():
                        break
                table[parent_row_index][0] = table[parent_row_index][0].strip() + " " + table[row_index][0].strip()
                empty_row_indices.append(row_index)
        num = 0
        for row_count in empty_row_indices:
            table.pop(row_count-num)
            num += 1
        return table
    
    def add_index_coloumn(self, table):
        for row_index in range(len(table)):
            index_col_val = ""
            if re.search(r'^[0-9]', table[row_index][0]):
                index_col_val = table[row_index][0].split(" ")[0]
                table[row_index][0] = table[row_index][0].split(index_col_val)[-1]
            table[row_index] = [index_col_val] + table[row_index]
        return table
    
    def add_new_headers(self, table):
        table[0][0] = "Index"
        table[0][1] = "Scheme Name"
        year_col_indices = []
        for col_index in range(len(table[0])):
            if re.search(r'[0-9]{4}\-[0-9]{4}', table[0][col_index]):
                year_col_indices.append(col_index)
        for col_index in year_col_indices:
            if not table[0][col_index-1].strip():  
                table[0][col_index-1] = table[0][col_index]
            elif not table[0][col_index+2].strip():
                table[0][col_index+2] = table[0][col_index]
            if not table[0][col_index+1].strip():  
                table[0][col_index+1] = table[0][col_index]
            col_index += 1
        table = self.merge_up_rows(0, table)
        return table

    def fix_second_header(self, table):
        header_row_index = None
        for row_index in range(len(table)):
            row = table[row_index]
            col_value = row[2].lower().strip()
            if col_value == SECOND_HEADER_FIELD:
                return table
            elif col_value == "budget":
                header_row_index = row_index
        if header_row_index:
            table = self.merge_up_rows(header_row_index, table)
        return table

    def merge_up_rows(self, row_index, table):
        for col_index in range(len(table[row_index])): 
            table[row_index][col_index] = (table[row_index][col_index].strip() + " " + table[row_index+1][col_index].strip()).strip()
        table.pop(row_index+1)
        return table

    def generate_expenditure_budgets_csv(self, doc_dir):
        for file_name in glob.glob("%s*.pdf" % doc_dir):
            department_name = os.path.basename(file_name).lower().split(".pdf")[0].decode('utf-8')
            if not department_name in SKIP_FILENAMES:
                logger.info("Processing PDF document for department: %s" % department_name)
                self.generate_csv_file(file_name, file_name.split(".pdf")[0] + ".csv")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files from Expenditure Budgets directory")
    parser.add_argument("doc_dir", help="Input directory path for Expenditure Budgets")
    args = parser.parse_args()
    obj = ExpenditureBudgetCSVGenerator()
    if not args.doc_dir: 
        print("Please input directory to begin CSV extraction")
    else:
        obj.generate_expenditure_budgets_csv(args.doc_dir)
