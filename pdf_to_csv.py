'Class for extracting CSV files from single table PDF documents'

import argparse
import numpy
import csv
import cv2
import logging
from logging.config import fileConfig
import os
from PyPDF2 import PdfFileReader
from reportlab.lib.pagesizes import A4, landscape
import re 

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()
BUFFER_LENGTH = 10
DEFAULT_PIXEL_COLOR = [255, 255, 255]
PAGE_BREAK_HANDLE = '"||page_break||"'

class PDF2CSV(object):
    def __init__(self):
        self.page_break = PAGE_BREAK_HANDLE
        self.temp_img_file = ''
        self.temp_csv_file = ''

    def generate_csv_file(self, input_pdf_filepath, out_csv_filepath, is_header=True, temp_file_postfix=""):
        input_pdf_obj = PdfFileReader(open(input_pdf_filepath, 'rb')) 
        total_pages = input_pdf_obj.getNumPages()
        department_name = os.path.basename(input_pdf_filepath).lower().split(".pdf")[0].decode('utf-8')
        temp_handle = re.sub(r'[^A-Za-z]', '_', department_name) 
        self.temp_img_file = '/tmp/pdf_image_%s%s.png' % (temp_handle, temp_file_postfix) 
        self.temp_csv_file = '/tmp/temp_data_%s%s.csv' % (temp_handle, temp_file_postfix)
        command = "rm -rf '%s'" % self.temp_csv_file
        os.system(command)
        for page_num in range(total_pages):
            page_layout = input_pdf_obj.getPage(page_num)['/MediaBox'] 
            page_width = float(page_layout[2])
            page_height = float(page_layout[3])
            command = "convert -density 300 '%s'[%s] '%s'" % (input_pdf_filepath, page_num, self.temp_img_file)
            os.system(command)
            self.image_object = cv2.imread(self.temp_img_file)
            image_height, image_width, channels = self.image_object.shape
            self.horizontal_ratio = page_width/image_width
            self.vertical_ratio = page_height/image_height
            lines = self.get_straight_lines()
            if lines.tolist():
                lines = self.extend_lines_for_table(lines, is_header)
            table_bounds = self.get_table_bounds()
            if table_bounds:
                command = "tabula --pages %s --area %s,%s,%s,%s '%s' >> '%s'" % (page_num+1, table_bounds["top"], table_bounds["left"], table_bounds["bottom"], table_bounds["right"], input_pdf_filepath, self.temp_csv_file) 
                logger.info("Processing: %s" % command)
                os.system(command)
            page_break_command = "echo '%s' >> '%s'" % (self.page_break, self.temp_csv_file)
            os.system(page_break_command)
        self.process_csv_file(out_csv_filepath)
    
    def get_straight_lines(self):
        '''Extract long straight lines using Probabilistic Hough Transform
        '''
        image_gray = cv2.cvtColor(self.image_object, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(image_gray, 100, 150, apertureSize = 3)
        min_line_length = 200
        max_line_gap = 100
        lines = cv2.HoughLinesP(edges, 1, numpy.pi/180, 80, min_line_length, max_line_gap)
        return lines

    def extend_lines_for_table(self, lines, is_header):
        '''Extend straight lines to identify table bounds
        '''
        found_horizontal_line = False
        found_vertical_line = False
        vertical_stretch = [0,0]
        horizontal_stretch = [0,0] 
        max_horizontal = [0,0,0,0]
        max_vertical = [0,0,0,0]
        horizontal_base_line = 0
        if is_header:
            horizontal_base_line = self.get_horizontal_base_line(lines)
        vertical_base_line = 0
        for line in lines:
            for x1,y1,x2,y2 in line:
                if x1 == x2:
                    if not found_vertical_line:
                        found_vertical_line = True
                    
                    length = (y1 - y2)
                    if max_vertical[0] <= length:
                        max_vertical[0] = length
                        max_vertical[1] = y1 + BUFFER_LENGTH
                        max_vertical[2] = y2 - BUFFER_LENGTH
                    if (max_vertical[3] == 0 or max_vertical[3] > (x1 - BUFFER_LENGTH)) and (x1 - BUFFER_LENGTH) > vertical_base_line: 
                        max_vertical[3] = (x1 - BUFFER_LENGTH)
                    horizontal_stretch = self.get_max_stretch(x1, horizontal_stretch)
                elif y1 == y2:
                    if not found_horizontal_line:
                        found_horizontal_line = True
                    length = (x2 - x1)
                    if max_horizontal[0] <= length:
                        max_horizontal[0] = length
                        max_horizontal[1] = x1 - BUFFER_LENGTH
                        max_horizontal[2] = x2 + BUFFER_LENGTH
                    if (max_horizontal[3] == 0 or max_horizontal[3] > (y1 - BUFFER_LENGTH)) and (y1 - BUFFER_LENGTH) > horizontal_base_line: 
                        max_horizontal[3] = (y1 - BUFFER_LENGTH)
                    if not is_header:
                        vertical_stretch = self.get_max_stretch(y1, vertical_stretch)
        if max_vertical[2] > max_horizontal[3] and max_horizontal[3] > 0:
            max_vertical[2] = max_horizontal[3]
        if max_horizontal[1] >  max_vertical[3] and max_vertical[3] > 0:
            max_horizontal[1] = max_vertical[3]
        if (not found_vertical_line and found_horizontal_line) or not is_header:
            max_vertical[1:3] = vertical_stretch 
        elif not found_horizontal_line and found_vertical_line:
            max_horizontal[1:3] = horizontal_stretch
        max_vertical = self.fix_vertical_lines(lines, max_vertical)
        for line in lines:
            for x1,y1,x2,y2 in line:
                if x1 == x2:
                    y1 = max_vertical[1]
                    y2 = max_vertical[2]
                elif y1 == y2:
                    x1 = max_horizontal[1]
                    x2 = max_horizontal[2]
                cv2.line(self.image_object,(x1,y1),(x2,y2),(0,0,0),4)
        cv2.line(self.image_object,(max_horizontal[2],max_vertical[1]),(max_horizontal[2],max_vertical[2]),(0,0,0),4)
        cv2.line(self.image_object,(max_horizontal[1],max_vertical[1]),(max_horizontal[1],max_vertical[2]),(0,0,0),4) 
        cv2.imwrite(self.temp_img_file, self.image_object)
        return lines

    def get_max_stretch(self, coordinate, stretch_vector):
        if stretch_vector[0] == stretch_vector[1] == 0:
            stretch_vector[0] = stretch_vector[1] = coordinate + BUFFER_LENGTH
        elif coordinate < stretch_vector[0]:
            stretch_vector[0] = coordinate - BUFFER_LENGTH
        elif coordinate > stretch_vector[1]:
            stretch_vector[1] = coordinate + BUFFER_LENGTH
        return stretch_vector

    def fix_vertical_lines(self, lines, max_vertical):
        image_height, image_width, channels = self.image_object.shape
        for line in lines:
            for x1,y1,x2,y2 in line:
                if x1 == x2:
                    while(self.image_object[y2, x2].tolist() != DEFAULT_PIXEL_COLOR and y2 > 0):
                        y2 -= 1
                    if y2 < max_vertical[2]:
                        max_vertical[2] = y2 
        return max_vertical

    def get_horizontal_base_line(self, lines):
        '''Gives vertical coordinate of horizontal base line(aka header line)
        '''
        horizontal_base_line = 0
        for line in lines:
            for x1,y1,x2,y2 in line:
                if y1 == y2 and (horizontal_base_line == 0 or horizontal_base_line > y1):
                    horizontal_base_line = y1 + BUFFER_LENGTH
        return horizontal_base_line
    
    def get_table_bounds(self):
        '''Get best possible table bounds
        '''
        table_bounds = None
        image_gray = cv2.cvtColor(self.image_object,cv2.COLOR_BGR2GRAY)
        temp_image, contours, hierarchy = cv2.findContours(image_gray,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        best_match_contour_index = None
        max_contour_size = 0
        count = 0
        for contour in contours:
            if cv2.contourArea(contour) > max_contour_size:
                contour_size = cv2.contourArea(contour)
                x,y,w,h = cv2.boundingRect(contour)
                if x>1 and y>1 and contour_size > max_contour_size:
                    best_match_contour_index = count
                    max_contour_size = contour_size
            count += 1
        if best_match_contour_index:
            x,y,w,h = cv2.boundingRect(contours[best_match_contour_index])
            x = x - BUFFER_LENGTH
            w = w + BUFFER_LENGTH
            cv2.rectangle(self.image_object,(x,y),(x+w,y+h),(0,0,0),2)
            table_bounds = {"top":y*self.vertical_ratio, "left":x*self.horizontal_ratio, "bottom":(h+y)*self.vertical_ratio, "right":(w+x)*self.horizontal_ratio}
            cv2.imwrite(self.temp_img_file, self.image_object)
        return table_bounds 

    def process_csv_file(self, out_csv_filepath): 
        '''Deletes empty rows and coloumns from table
        '''
        table = []
        empty_coloumns = []
        total_col_count = 0
        is_row_len_consistent = True
        with open(self.temp_csv_file, 'rb') as in_csv_file:
            csv_reader = csv.reader(in_csv_file, delimiter=',')
            for row in csv_reader:
                if ''.join(row).strip():
                    table.append(row)
                    if total_col_count == 0:
                        total_col_count = len(row)
                    elif total_col_count != len(row):
                        is_row_len_consistent = False
        if is_row_len_consistent:
            for col_count in range(len(table[0])):
                total_col_val = ""
                for row_count in range(len(table)):
                    total_col_val += table[row_count][col_count]
                if not total_col_val.strip():
                    empty_coloumns.append(col_count)
        for row in table:
            num = 0
            for col_count in empty_coloumns:
                row.pop(col_count-num)
                num += 1
        table = self.modify_table_data(table)
        if not table:
            return
        out_csv_file = open(out_csv_filepath, "wb")
        csv_writer = csv.writer(out_csv_file, delimiter=',')
        for row in table:
            if not row[0] == self.page_break.replace('"',''): 
                csv_writer.writerow(row)
        out_csv_file.close()

    def delete_empty_coloumns(self, table):
        '''Deletes empty coloumns generated from Tabula
        '''
        empty_coloumns = []
        for col_count in range(len(table[0])):
            total_col_val = ""
            for row_count in range(len(table)):
                total_col_val += table[row_count][col_count]
            if not total_col_val.strip():
                empty_coloumns.append(col_count)
        for row in table:
            num = 0
            for col_count in empty_coloumns:
                row.pop(col_count-num)
                num += 1
        return table
    
    def modify_table_data(self, table):
        '''Opportunity for inheriting classes to modify table data as per individual needs
        '''
        return table

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extracts CSV file from single table PDF document(A4)")
    parser.add_argument("--header", help="Use if file consists of a page header(& we need to skip it)")
    parser.add_argument("input_file", help="Input PDF filepath")
    parser.add_argument("output_file", help="Output CSV filepath")
    args = parser.parse_args()
    args = parser.parse_args()
    obj = PDF2CSV()
    if not args.input_file or not args.output_file: 
        print("Please pass input and output filepaths")
    else:
        obj.generate_csv_file(args.input_file, args.output_file, is_header=args.header)
