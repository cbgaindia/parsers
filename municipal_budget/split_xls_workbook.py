import argparse
import logging
from logging.config import fileConfig
import os
import re
import sys
import xlrd
import xlwt
from xlutils.copy import copy

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()
reload(sys)
sys.setdefaultencoding('utf-8')
CURRENCY_SLUG = "lakh|lakhs|'000"
CURRENCY_INDEX_LIMIT = 10 
INVAILD_SHEET_SLUG = "working|notes|reconcil"

class SplitWorkbooks():
    def generate_xls_files(self, input_file, output_dir):
        input_file = self.convert_file_into_xls(input_file)
        logger.info("Processing input file: %s" % input_file)
        input_workbook = xlrd.open_workbook(input_file, formatting_info=True)
        total_sheets = input_workbook.nsheets
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        for sheet_number in xrange(total_sheets):
            if re.findall(r"^(%s)" % INVAILD_SHEET_SLUG, input_workbook.sheet_by_index(sheet_number).name.lower()):
                continue
            worksheet_name = self.get_worksheet_name(input_workbook, sheet_number)
            output_workbook = copy(input_workbook)
            output_workbook._Workbook__worksheets = [output_workbook._Workbook__worksheets[sheet_number]]
            output_workbook.set_active_sheet(0)
            file_name = worksheet_name.replace("/", '|')
            output_file = output_dir + "/" + file_name + ".xls"
            output_workbook.save(output_file)

    def convert_file_into_xls(self, input_file):
        input_file_format = input_file.split(".")[-1] 
        if input_file_format == "xlsx":
            temp_file_name = os.path.dirname(input_file) + "/temp.xls"
            os.system("unoconv -f xls -o '%s' '%s'" % (temp_file_name, input_file))
            return temp_file_name
        elif input_file_format == "xls":
            return input_file
        else:
            logger.error("Script expects input file to be xls or xlsx")
            sys.exit(0)

    def get_worksheet_name(self, input_workbook, sheet_number):
        worksheet = input_workbook.sheet_by_index(sheet_number)
        worksheet_name = ""
        for row_index in xrange(worksheet.nrows):
            print(row_index)
            row_value_join = "".join([str(x).encode('string_escape') for x in worksheet.row_values(row_index)]).strip() 
            if not row_value_join:
                continue
            elif re.findall(r"%s" % str(CURRENCY_SLUG), row_value_join.lower()) and row_index <= CURRENCY_INDEX_LIMIT:
                break
            for col_num in xrange(len(worksheet.row_values(row_index))):
                if str(worksheet.row_values(row_index)[col_num]).strip():
                    worksheet_name = str(worksheet.row_values(row_index)[col_num]).strip() 
                    break
            print(worksheet_name)
        return worksheet_name
                    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates XLS files from Municipal Budget XLSX Document")
    parser.add_argument("input_file", help="Input filepath for budget document")
    parser.add_argument("output_dir", help="Output directory for budget document")
    args = parser.parse_args()
    obj = SplitWorkbooks()
    if not args.input_file or not args.output_dir: 
        print("Please input file and output directory to save split XLS files")
    else:
        obj.generate_xls_files(args.input_file, args.output_dir)    
