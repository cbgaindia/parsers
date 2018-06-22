import argparse
import csv
import glob
import logging
from logging.config import fileConfig
import os
import re
import sys
import xlrd

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()
reload(sys)
sys.setdefaultencoding('utf-8')
FILE_REGEX = "Demand|Budget at a glance|Receipt"
BUDGET_START_SLUG = "Actual|Budget"
CURRENCY_SLUG_REGEX = "\(In Thousands of Rupees\)|\(Rupees in thousand\)|\( In Lakhs of Rupees\)|\(Rs. in thousand\)"
HEADER_ROWS_NUM = 3
NOTES_SLUG = "Notes:|Note:"

class SikkimBudgetCSVGenerator():
    def __init__(self):
        self.currency_handle = ""    

    def process_budget_files(self, input_dir):
        budget_files = self.find_files_for_conversion(input_dir)
        for input_file in budget_files:
            logger.info("Processing input: %s" % input_file)
            workbook = xlrd.open_workbook(input_file)
            worksheet = workbook.sheet_by_index(0)
            file_name = "".join(worksheet.row_values(0)).strip() + " - " + "".join(worksheet.row_values(1)).strip() 
            start_index = 0
            for row_index in xrange(2, worksheet.nrows): 
                row_value_join = "".join([str(x).encode('string_escape') for x in worksheet.row_values(row_index)]).strip()
                matched_currency_handle = re.findall(r"%s" % CURRENCY_SLUG_REGEX, row_value_join)
                if matched_currency_handle:
                    self.currency_handle = matched_currency_handle[0]
                    start_index = row_index+1
                    break
            header_row = self.create_file_header(worksheet, start_index)
            self.create_csv_file(worksheet, start_index, header_row, file_name, input_file)

    def create_file_header(self, worksheet, start_index):
        header_row = []
        budget_values_start_index = 0
        for index in range(start_index, start_index+HEADER_ROWS_NUM):
            temp_header = worksheet.row_values(index)
            for col_index in range(len(temp_header)):
                if not budget_values_start_index and re.findall(r"%s" % BUDGET_START_SLUG, str(temp_header[col_index]).strip()):
                    budget_values_start_index = col_index
                temp_header[col_index] = str(temp_header[col_index]).replace("\n", " ").strip()
                temp_header[col_index] = re.sub(r"\s{2,}", " ", temp_header[col_index])
                if budget_values_start_index and col_index > budget_values_start_index and not temp_header[col_index].strip():
                    temp_header[col_index] = temp_header[col_index-1]
                if len(header_row)-1 < col_index:
                    header_row.append(temp_header[col_index]) 
                elif temp_header[col_index].strip():
                    header_row[col_index] += " " + temp_header[col_index]
        for index in range(budget_values_start_index, len(header_row)):
            header_row[index] = header_row[index] + " " + self.currency_handle
        if not header_row[0].strip(): 
            header_row[0] = "Major Head and Totals"
        if not header_row[1].strip(): 
            header_row[1] = "Budget Head"
        return header_row

    def create_csv_file(self, worksheet, start_index, header_row, file_name, input_file):
        output_dir = "/".join(input_file.split("/")[0:-1]) 
        out_csv_file = open(output_dir + "/" + file_name + ".csv", "wb")
        csv_writer = csv.writer(out_csv_file, delimiter=',')
        csv_writer.writerow(header_row)
        col_index_join = "".join(str(float(x)) for x in range(1,len(header_row)+1))
        for row_index in xrange(start_index+HEADER_ROWS_NUM, worksheet.nrows):
            row_value_join = "".join([str(x).encode('string_escape') for x in worksheet.row_values(row_index)]).strip() 
            if not row_value_join or row_value_join == col_index_join or re.findall(r"%s" % NOTES_SLUG, str(worksheet.row_values(row_index)[0])):
                continue
            else:
                csv_writer.writerow(worksheet.row_values(row_index))      
        out_csv_file.close()

    def find_files_for_conversion(self, input_dir):
        budget_files = []
        files = glob.glob('%s/**/**/*.xls*' % input_dir)
        files += glob.glob('%s/**/**/*.XLS' % input_dir)
        for file_name in files:
            if re.findall(r"%s" % FILE_REGEX, file_name):
                budget_files.append(file_name)
        return budget_files

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files for Sikkim Budget(from XLSX & XLS Documents)")
    parser.add_argument("input_dir", help="Input directory for budget documents")
    args = parser.parse_args()
    if not args.input_dir:
        logger.error("Please input directory to begin CSV extraction")
    else: 
        obj = SikkimBudgetCSVGenerator()
        obj.process_budget_files(args.input_dir)
