import argparse
import csv
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
CURRENCY_SLUG = "lakh|lakhs|'000"
CURRENCY_INDEX_LIMIT = 10 
LEGEND_SLUG = "legend"

class MunicipalXLSX2CSV():
    def generate_budget_csv_files(self, input_file, output_dir):
        workbook = xlrd.open_workbook(input_file)
        total_sheets = workbook.nsheets
        for sheet_number in xrange(total_sheets):
            worksheet = workbook.sheet_by_index(sheet_number)
            worksheet_name = ""
            for row_index in xrange(worksheet.nrows):
                row_value_join = "".join([str(x).encode('string_escape') for x in worksheet.row_values(row_index)]).strip() 
                if not row_value_join:
                    continue
                elif re.findall(r"%s" % str(CURRENCY_SLUG), row_value_join.lower()) and row_index <= CURRENCY_INDEX_LIMIT:
                    self.generate_csv_file(worksheet, worksheet_name, row_index, output_dir)
                    break
                if str(worksheet.row_values(row_index)[0]).strip():
                    worksheet_name = str(worksheet.row_values(row_index)[0]).strip() 
                if str(worksheet.row_values(row_index)[1]).strip():
                    worksheet_name = str(worksheet.row_values(row_index)[1]).strip() 

    def generate_csv_file(self, worksheet, worksheet_name, start_index, output_dir):
        if not worksheet_name:
            worksheet_name = worksheet.name
        logger.info("Generating CSV file for Sheet: %s ||| %s" % (str(worksheet.name), worksheet_name))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        file_name = worksheet_name.replace("/", '|')
        out_csv_file = open(output_dir + "/" + file_name + ".csv", "wb")
        csv_writer = csv.writer(out_csv_file, delimiter=',')
        for row_index in xrange(start_index+1, worksheet.nrows):
            row_value_join = "".join([str(x).encode('string_escape') for x in worksheet.row_values(row_index)]).strip() 
            if not row_value_join:
                continue
            elif row_value_join.lower() == LEGEND_SLUG:
                break
            else:
                csv_writer.writerow([str(x).replace("\n", " ") for x in worksheet.row_values(row_index)])
        out_csv_file.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates CSV files from Municipal Budget XLSX Document")
    parser.add_argument("input_file", help="Input filepath for budget document")
    parser.add_argument("output_dir", help="Output directory for budget document")
    args = parser.parse_args()
    obj = MunicipalXLSX2CSV()
    if not args.input_file or not args.output_dir: 
        print("Please input file and output directory to begin CSV extraction")
    else:
        obj.generate_budget_csv_files(args.input_file, args.output_dir)    
