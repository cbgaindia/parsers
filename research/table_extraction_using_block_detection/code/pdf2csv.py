'''The execution script to convert a folder of ddg pdfs to ddg csvs
'''
import os
import subprocess
import argparse
import cv2
import pandas as pd
from image_to_block_feature_generator import (BlockTextualFeatureGenerator,
                                              filter_unwanted_blocks,
                                              separate_blocks)
from block_labeler import (BlockLabeler,
                           mark_tables_using_titles,
                           combine_headers,
                           combine_horizontal,
                           remove_false_headers,
                           mark_groupings_using_rf_model)
from labelled_blocks_to_csv import BlocksToCSV
from demand_draft_generator import combine_tables
from PyPDF2 import PdfFileReader


def fill_major_head(row):
    '''Helper function to fill major head where not present.
    '''
    if pd.isnull(row['major_head']) and pd.notnull(row['head_of_account']):
        row['major_head'] = row['head_of_account']
    return row


def get_page_width_height(pdf, page_num):
    '''Check orientation and extract width and height of a pdf page.
    '''
    page_layout = pdf.getPage(page_num)['/MediaBox']
    if '/Rotate' in pdf.getPage(page_num) and pdf.getPage(page_num)['/Rotate'] == 90:
        page_width = float(page_layout[3])
        page_height = float(page_layout[2])
    else:
        page_width = float(page_layout[2])
        page_height = float(page_layout[3])
    return page_width, page_height


def get_page_image_from_pdf(pdf_file_path, page_num, image_file_name):
    '''Extract pdf page as image.
    '''
    command = 'convert -density 300 "%s"[%s] "%s"' % (pdf_file_path,
                                                      page_num,
                                                      image_file_name)
    subprocess.check_output(command, shell=True)
    return cv2.imread(image_file_name, 0)

def check_and_create_folder(path):
    '''Check if the folder exists, if not create it.
    '''
    if not os.path.isdir(path):
        os.makedirs(path)
    return True


def save_binary_image(blocked_image, save_path):
    '''We work on binary images but to save images the opencv write functions
    expects the range of 0 - 255 thus we do a simple replace and save images.
    '''
    blocked_image[blocked_image == 1] = 255
    cv2.imwrite(save_path, blocked_image)
    return True


def unprocessed_files(input_folder, output_folder):
    '''
    Check which pdfs are already generated and remove them from the complete
    list of pdfs.
    '''
    processed_pdfs = [name + ".pdf" for name in os.listdir(output_folder)
                      if os.path.isdir(os.path.join(output_folder, name))]
    return list(set(os.listdir(input_folder)) - set(processed_pdfs))


def process_folder(input_folder_path, output_folder_path, resume):
    '''Process a folder of demand draft pdfs and store the output in the output
    folder.
    '''
    pdf_files = os.listdir(input_folder_path)
    if resume > 0:
        pdf_files = unprocessed_files(input_folder_path, output_folder_path)
        print('processing: {0}'.format(pdf_files))
    #for pdf_file_name in ["11. LA, Governor's Secretariat, Council of Ministers, Agricultural Marketing, Agri.pdf"]:
    for pdf_file_name in pdf_files:
        target_folder = os.path.join(output_folder_path,
                                     pdf_file_name.strip('.pdf'))
        tables = pd.DataFrame()
        pdf_file_path = os.path.join(input_folder_path, pdf_file_name)
        pdf = PdfFileReader(open(pdf_file_path, 'rb'))
        num_pages = pdf.getNumPages()
        # skip first n pages to skip the index
        # TODO: move this to config.
        for page_num in range(2, num_pages):
            page_width, page_height = get_page_width_height(pdf, page_num)
            img_page = get_page_image_from_pdf(pdf_file_path, page_num, 'tmp.png')
            image_height, image_width = img_page.shape
            horizontal_ratio = page_width / image_width
            vertical_ratio = page_height / image_height
            dilate = True
            feature_extractor = BlockTextualFeatureGenerator(img_page, horizontal_ratio,
                                                             vertical_ratio,
                                                             page_num,
                                                             pdf_file_path,
                                                             (25, 20),
                                                             [filter_unwanted_blocks,
                                                              separate_blocks],
                                                             dilate)
            block_features = feature_extractor.generate()
            images_log_folder = os.path.join(target_folder, 'log_images')
            check_and_create_folder(images_log_folder)
            save_binary_image(feature_extractor.img_with_blocks,
                              '{0}/{1}.png'.format(images_log_folder, page_num))
            features_log_folder = os.path.join(target_folder, 'log_block_features')
            check_and_create_folder(features_log_folder)
            block_features.to_csv('{0}/{1}.csv'.format(features_log_folder,
                                                       page_num), index=False)
            # Blank page check
            if len(block_features.index) > 3:
                block_features_with_labels = BlockLabeler(block_features,
                                                          post_processors=[mark_tables_using_titles,
                                                                           combine_headers,
                                                                           combine_horizontal,
                                                                           remove_false_headers,
                                                                           mark_groupings_using_rf_model
                                                                          ]).label()

                block_features_with_labels.to_csv('{0}/{1}_labelled.csv'.format(features_log_folder,
                                                                                page_num),
                                                  index=False)
                try:
                    page_tables = BlocksToCSV(img_page,
                                              block_features_with_labels,
                                              page_num,
                                              target_folder).write_to_csv()
                    tables = pd.concat([tables, pd.DataFrame(page_tables)])
                except Exception as err:
                    print(err)
                    print(page_num, pdf_file_name)
        tables.to_csv('{0}/raw_tables_features.csv'.format(target_folder), index=False)
        tables.demand_no = tables.demand_no.fillna(method='ffill')
        tables = tables.apply(fill_major_head, axis=1)
        tables.major_head = tables.major_head.fillna(method='ffill')
        tables.to_csv('{0}/tables_features.csv'.format(target_folder), index=False)
        combine_tables(tables[tables.detailed == True], target_folder)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Extracts CSV from a folder of pdfs.")
    arg_parser.add_argument("input_folder", help="Input PDF folder")
    arg_parser.add_argument("output_folder", help="Output folder")
    arg_parser.add_argument("--resume", default=0, type=int,
                            help="Resume previous running process.")
    input_args = arg_parser.parse_args()
    process_folder(input_args.input_folder, input_args.output_folder,
                   input_args.resume)
