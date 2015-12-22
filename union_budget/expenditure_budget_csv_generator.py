'CSV generator for Expenditure Budget PDFs'

import argparse
import glob
import logging
from logging.config import fileConfig
import re
import os
from parsers.pdf_to_csv import PDF2CSV
from parsers.keywords_extractor import KeywordsExtractor

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()

SKIP_FILENAMES = ["all statements of budget estimates"]
SECOND_HEADER_FIELD = "budget support"
FIRST_HEADER_ROW = ['Index', 'Scheme', '', 'Actual', 'Actual', 'Actual', 'Budget', 'Budget', 'Budget', 'Revised', 'Revised', 'Revised', 'Budget', 'Budget', 'Budget']
SECOND_HEADER_ROW = ['', 'Head of Development', 'Budget Support', 'IEBR', 'Total', 'Budget Support ', 'IEBR', 'Total', 'Budget Support', 'IEBR', 'Total', 'Budget Support', 'IEBR ', 'Total']
HEADER_STUBS = ["HeadPlan", "HeadofDevB"]
MIN_COL_COUNT = 5
class ExpenditureBudgetCSVGenerator(PDF2CSV):
    def __init__(self):
        super(ExpenditureBudgetCSVGenerator, self).__init__()
        self.header_rows_indices = [0,1,2]
        self.header_rows_cap = 5
        self.keywords_extractor = KeywordsExtractor()        
        self.bold_keywords = []

    def modify_table_data(self, table):
        table = self.merge_splitted_coloumns(table)
        if not table:
            return table
        table = self.split_merged_coloumns(table)
        table = self.fix_second_header(table)
        table = self.remove_dulicate_headers(table)
        empty_row_indices = []
        for row_num in range(len(table)-1):
            if "".join(table[row_num]).strip() == "Major" and table[row_num+1][1].strip() == "Head":
                table[row_num+1][1] = "Major " + table[row_num+1][1] 
                table[row_num][1] == ""
                empty_row_indices.append(row_num)
        for row_count in empty_row_indices:
            table.pop(row_count)
        table = self.merge_splitted_rows(table)
        table = self.ensure_table_intergrity(table)
        table = self.add_index_coloumn(table)
        table = self.add_new_headers(table)
        return table

    def merge_splitted_coloumns(self, table):
        pagewise_table_list = []
        temp_list = []
        for row in table:
            if row[0] == self.page_break.replace('"',''):
                if temp_list and len(temp_list[0]) > MIN_COL_COUNT:
                    pagewise_table_list.append(temp_list)
                    temp_list = []
            elif len(row) > MIN_COL_COUNT:
                row[0] = row[0].strip()
                row[1] = row[1].strip()
                if re.search(r'^[\d\.]+$', row[0]) and row[1]:
                    row[0] += " " + row[1] 
                    row[1] = ""  
                temp_list.append(row)
        if temp_list and len(temp_list[0]) > MIN_COL_COUNT:
            pagewise_table_list.append(temp_list)
        table = [] 
        for page_table in pagewise_table_list:
            page_table = self.delete_empty_coloumns(page_table)
            for row_index in range(len(page_table)):
                while page_table[row_index][0].strip() == page_table[row_index][1].strip() == "":
                    page_table[row_index][0] += " " + page_table[row_index][1]
                    page_table[row_index].pop(1)
            header_row = page_table[1]
            merge_upper_bound = 0
            for col_index in range(1, len(header_row)):
                header_stub = header_row[col_index].strip().lower() 
                if re.search(r"^(major|head of dev*)$", header_stub):
                    merge_upper_bound = col_index
                    break
            for row in page_table:
                if merge_upper_bound:
                    num = 0
                    row[0] = row[0].strip()
                    for col_index in range(1, merge_upper_bound):
                        row[0] += " " + row[col_index-num]
                        row.pop(col_index-num)
                        num += 1
                table.append(row)
        return table
    
    def split_merged_coloumns(self, table):
        for row in table:
            for col_index in range(2,len(row)):
                if re.search(r'^(\.{3}\s(\.{3}|[0-9]|\-[0-9]))', row[col_index].strip()) and not row[col_index-1].strip():
                    row[col_index-1] = "..."
                    row[col_index] = re.sub(r'^\.{3}\s', '', row[col_index]).strip()
        new_col_indices = []
        for row_index in range(len(table)):
            row = table[row_index]
            new_col_values_map = {}
            for col_index in range(0, len(row)):
                row[col_index] = row[col_index].strip()
                multi_col_match = re.search(r'^((\.{3}|(\-)*[0-9]+(\.[0-9]+){,1}|Plan|Non-Plan|Total)(\s)*)+$', row[col_index].strip())
                if multi_col_match:
                    multi_col_match_str = multi_col_match.group(0)
                    if " " not in multi_col_match_str.strip():
                        continue
                    col_values = multi_col_match_str.split(" ")
                    row[col_index] = col_values[0]
                    index_correction = len(new_col_values_map)
                    for col_count in range(1,len(col_values)):
                        if col_index+col_count < len(row) and not row[col_index+col_count].strip():
                            row[col_index+col_count] = col_values[col_count]
                        else:
                            insert_pointer = col_index+col_count+index_correction 
                            new_col_values_map[insert_pointer] = col_values[col_count] 
                            if not insert_pointer in new_col_indices and row_index <= self.header_rows_cap:
                                new_col_indices.append(insert_pointer)
            for index in sorted(new_col_values_map):
                row.insert(index, new_col_values_map[index])
        table = self.correct_major_head_values(table)
        col_shifted = False
        for row_index in range(len(table)):
            table[row_index][0] = table[row_index][0].strip()  
            table[row_index][1] = table[row_index][1].strip()  
            if (re.match(r'head of', table[row_index][1].lower()) and re.match(r'budget', table[row_index][2].strip().lower())):
                continue
            if len(table[row_index]) > len(SECOND_HEADER_ROW) or not " " in " ".join(table[row_index]).strip():
                while not table[row_index][0] and "".join(table[row_index][1:]).strip():
                    table[row_index].pop(0)
                    col_shifted = True
        if col_shifted:
            table = self.correct_major_head_values(table)
        for col_index in new_col_indices:
            table[0].insert(col_index, " ")
        return table
       
    def correct_major_head_values(self, table):
        for row in table:
            major_code_match = re.findall(r'[0-9]{4,}$', row[0].strip())
            if major_code_match and len(row) < len(SECOND_HEADER_ROW):
                major_code = major_code_match[-1]
                scheme_name = row[0].split(major_code)[0]
                row[0] = scheme_name.strip()
                if not row[1].strip():
                    row[1] = major_code
                else:
                    row.insert(1, major_code)
        for row_index in range(2, len(table)):
            major_head_cell_val = table[row_index][1].strip() 
            if not major_head_cell_val or (re.match(r'head of', major_head_cell_val.lower()) and re.match(r'budget', table[row_index][2].strip().lower())):
                continue
            if re.search(r'(^[0-9]{1,}\.[0-9]{1,})|\.{3}', major_head_cell_val):
                table[row_index].insert(1, '')
            elif re.search(r'\D{2,}(\s\D{2,})+', major_head_cell_val):
                major_code_match = re.search(r'\d{4,}', major_head_cell_val)
                if major_code_match:
                    major_code = major_code_match.group(0)
                    table[row_index][0] += table[row_index][0].strip() + " " + major_head_cell_val.split(major_code)[0].strip()
                    table[row_index][1] = major_code
                else:
                    table[row_index][0] = major_head_cell_val
                    table[row_index][1] = ""
        return table
    
    def remove_dulicate_headers(self, table):
        empty_row_indices = []
        header_rows = []
        seconary_header_stub = "".join(SECOND_HEADER_ROW).replace(" ", "")
        for row_num in self.header_rows_indices:
            header_rows.append("".join(table[row_num]).replace(" ", ""))
        for row_num in range(self.header_rows_indices[-1]+1, len(table)):
            row_stub = "".join(table[row_num]).replace(" ", "")
            if row_stub in header_rows or re.search(r"^(%s)" % "|".join(HEADER_STUBS), row_stub):
                empty_row_indices.append(row_num)
            if row_stub == seconary_header_stub and not seconary_header_stub in header_rows:
                header_rows.append(seconary_header_stub)
            elif "IEBR" in row_stub:
                empty_row_indices.append(row_num)
        num = 0
        for row_count in empty_row_indices:
            table.pop(row_count-num)
            num += 1
        return table

    def merge_splitted_rows(self, table):
        empty_row_indices = []
        for row_index in range(1,len(table)):
            table[row_index][0] = table[row_index][0].strip()
            if not table[row_index][0] or re.search(r'^([0-9]|Total|[A-C]\.)|\:$', table[row_index][0]) or (table[row_index][0].lower() in self.bold_keywords): 
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
            table[row_index][0] = table[row_index][0].strip() 
            if re.search(r'^(\d{1,2}(\.)*)+(\s){0,1}\D+', table[row_index][0]):
                index_col_val = table[row_index][0].split(" ")[0]
                table[row_index][0] = table[row_index][0].split(index_col_val)[-1]
            table[row_index] = [index_col_val] + table[row_index]
        return table
    
    def add_new_headers(self, table):
        year_list = []
        header_size = len(table[0])
        for col_index in range(header_size):
            year_data_match = re.search(r'[0-9]{4}\-[0-9]{4}', table[0][col_index])
            if year_data_match:
                year = year_data_match.group(0)
                year_list.append(year)
        table[0] = FIRST_HEADER_ROW[:]
        num = 3
        for year in year_list:
            for val in range(0,3):
                table[0][num] += " " + year
                num += 1
        while len(table[0]) > len(table[1]):
            table[1] = [""] + table[1]
        table = self.merge_up_rows(0, table)
        return table

    def fix_second_header(self, table):
        merge_up_required = False
        header_row_index = None
        for row_index in range(len(table)):
            row = table[row_index]
            col_value = row[2].lower().strip()
            if col_value == SECOND_HEADER_FIELD:
                header_row_index = row_index
                table[header_row_index] = SECOND_HEADER_ROW[:]
            elif re.match("^Head of", "".join(row).strip()):
                header_row_index = row_index
                table[header_row_index] = SECOND_HEADER_ROW[:]
                merge_up_required = True
                break
        if merge_up_required:
            table.pop(header_row_index+1)
        return table

    def merge_up_rows(self, row_index, table):
        for col_index in range(len(table[row_index])): 
            table[row_index][col_index] = (table[row_index][col_index].strip() + " " + table[row_index+1][col_index].strip()).strip()
        table.pop(row_index+1)
        return table

    def generate_expenditure_budgets_csv(self, doc_dir):
        year_data_match = re.search(r'[0-9]{4}\-[0-9]{2,}', doc_dir) 
        if year_data_match:
            year = year_data_match.group(0) 
        for file_name in glob.glob("%s*.pdf" % doc_dir):
            department_name = os.path.basename(file_name).lower().split(".pdf")[0].decode('utf-8')
            if not department_name in SKIP_FILENAMES:
                logger.info("Processing PDF document for department: %s" % department_name)
                try:
                    self.bold_keywords = self.keywords_extractor.get_bold_text_phrases(file_name, is_other_starting_phrases=True, single_word=True)
                    logger.info("BOLD Keywords: %s" % str(self.bold_keywords))
                    self.generate_csv_file(file_name, file_name.split(".pdf")[0] + ".csv", temp_file_postfix=year)
                except Exception, error_message:
                    logger.error("Unable to extract CSV for department: %s, error_message: %s" % (department_name, error_message), exc_info = True)

    def ensure_table_intergrity(self, table):
        for row in table:
            if len(row) > len(SECOND_HEADER_ROW):
                col_to_delete = []
                for col_index in range(1, len(row)):
                    if not row[col_index].strip():
                        col_to_delete.append(col_index)
                if col_to_delete:
                    num = 0
                    for col_index in col_to_delete:
                        row.pop(col_index-num)
                        num += 1
            while len(row) < len(SECOND_HEADER_ROW):
                row.append("")
        return table

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files from Expenditure Budgets directory")
    parser.add_argument("doc_dir", help="Input directory path for Expenditure Budgets")
    args = parser.parse_args()
    obj = ExpenditureBudgetCSVGenerator()
    if not args.doc_dir: 
        print("Please input directory to begin CSV extraction")
    else:
        obj.generate_expenditure_budgets_csv(args.doc_dir)
