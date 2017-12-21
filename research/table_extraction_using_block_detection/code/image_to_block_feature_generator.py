'''Classes that can consume images to generate blocks and their features
(textual and geometrical)
'''
from itertools import groupby
from collections import Counter
import re
import subprocess
import cv2
import pandas as pd
import numpy as np


class ImageToBlocks(object):
    '''Convert Images to images with block like structures.

    Args:
        - img (obj:`numpy.Array`): A numpy array of the image.
        - block_threshold (tuple:(int, int)): A tuple containing threshold params
            namely vertical and horizontal for block generation.
    '''
    def __init__(self, img, block_threshold):
        self.img = img
        self.block_threshold = block_threshold

    def generate_blocks(self):
        '''Generate blocked image from images of pdf pages using custom implementation of Run
        Length Smoothing Algorithm (RLSA)

        Returns:
            Image with blocked structures.

        NOTE: This method is slow and will be removed in the coming iterations.
        '''
        _, thresh1 = cv2.threshold(self.img, 0, 1, cv2.THRESH_BINARY_INV)
        img_iter = np.nditer(thresh1, flags=['multi_index'])
        c_vertical, c_horizontal = self.block_threshold
        temp_thresh = thresh1.copy()
        while not img_iter.finished:
            point_x, point_y = img_iter.multi_index
            x_threshold = point_x + c_horizontal
            y_threshold = point_y + c_vertical
            neg_x_threshold = point_x - c_horizontal
            neg_y_threshold = point_y - c_vertical
            if (thresh1[point_x:x_threshold, point_y:y_threshold].any()
                    or thresh1[point_x:x_threshold, point_y:neg_y_threshold].any()
                    or thresh1[point_x:neg_x_threshold, point_y:y_threshold].any()
                    or thresh1[point_x:neg_x_threshold, point_y:neg_y_threshold].any()):
                temp_thresh[point_x, point_y] = 1
            else:
                temp_thresh[point_x, point_y] = 0
            img_iter.iternext()
        return temp_thresh

    def generate_blocks_dilation(self):
        '''Generate blocked images from images of pdf pages using opencv's
        dilate function.
 
        https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_imgproc/py_morphological_ops/py_morphological_ops.html#dilation
        '''
        kernel = np.ones((5, 10), np.uint8)
        _, thresh1 = cv2.threshold(self.img, 0, 1, cv2.THRESH_BINARY_INV)
        return cv2.dilate(thresh1, kernel, iterations=4)


class BlockGeometricalFeatureGenerator(ImageToBlocks):
    '''Extract geometrical feature for each block in a dataframe.

    Args:
        - img (obj:`numpy.Array`): A numpy array of the image.
        - block_threshold (tuple:(int, int)): A tuple containing threshold params
            namely vertgenerical and horizontal for block generation.
    '''
    def __init__(self, img, block_threshold, dilate=False):
        self.dilate = dilate
        self.image_with_blocks = None
        super(BlockGeometricalFeatureGenerator, self).__init__(img, block_threshold)

    @staticmethod
    def __get_block_stats_df(stats, centroids):
        '''Convert stats from cv2.connectedComponentsWithStats to dataframe.

        Args:
            - stats (obj:`numpy.Array`): the stats generated from openCV

        Returns:
            A dataframe with stats
        '''
        stats_columns = ["left", "top", "width", "height", "area"]
        block_stats = pd.DataFrame(stats, columns=stats_columns)
        block_stats['centroid_x'], block_stats['centroid_y'] = centroids[:, 0], centroids[:, 1]
        # Ignore the label 0 since it is the background
        block_stats.drop(0, inplace=True)
        return block_stats

    def extract_block_stats(self):
        '''Extract Geometrical features from img with blocks.

        Returns:
            A dataframe with each row as block and its geom features.
        '''
        if self.dilate:
            self.img_with_blocks = self.generate_blocks_dilation()
        else:
            self.img_with_blocks = self.generate_blocks()
        _, _, stats, centroids = cv2.connectedComponentsWithStats(self.img_with_blocks)
        block_stats = self.__get_block_stats_df(stats, centroids)
        block_stats['right'] = block_stats.left + block_stats.width
        block_stats['bottom'] = block_stats.top + block_stats.height
        block_stats['pos'] = block_stats.index
        return block_stats

    @staticmethod
    def overlay_img_with_blocks(img, blocks):
        '''A utility function to overlay blocked image over the actual image.
        '''
        raise NotImplementedError('To be Implemented in Version 0.2')


class BlockTextualFeatureGenerator(BlockGeometricalFeatureGenerator):
    '''Extract Textual Features of each block.

    Args:
        - img (obj:`numpy.Array`): Matrix form of the image.
        - horizontal_ratio (float): ratio of page_width and image_width.
        - vertical_ratio (float): ratio of page_height and image_height.
        - page_num (int): Page number from where to read the text.
        - pdf_file_path (string): Path of the pdf file.
        - block_threshold (tuple:(int, int)): A tuple containing threshold params
            namely vertical and horizontal for block generation.
        - post_processors (list:[functions]): A list of functions that can process
            the blocks generated.
    '''
    TEXT_REGEX = '[a-zA-Z_]+'
    COMMA_SEP_REGEX = r'^-?(\d+)(,\s*\d+)*$'

    def __init__(self, img, horizontal_ratio,
                 vertical_ratio, page_num,
                 pdf_file_path, block_threshold,
                 post_processors=[],
                 dilate=False):
        #image params
        self.img = img
        self.block_threshold = block_threshold
        # these are required for scaling boundaries while reading text.
        self.horizontal_ratio = horizontal_ratio
        self.vertical_ratio = vertical_ratio
        # We would need the pdf path and page num to extract text from the pdf using pdf2txt
        self.pdf_file_path = pdf_file_path
        self.page_num = page_num
        # post processors
        self.post_processors = post_processors
        self.dilate = dilate

    @staticmethod
    def check_text_for_continous_dashes(text):
        '''
        Check if the text in the block contains continous dashes.
        '''
        for char, count in [[k, len(list(g))] for k, g in groupby(text)]:
            if char == '-' and count > 2:
                return True
        return False

    def get_text_from_pdf(self, point_x, point_y, width, height):
        '''Extract text of a given block from the pdf
        '''
        cmd_ext = 'pdftotext'
        cmd_page_params = ' -f {0} -l {0}'.format(self.page_num + 1)
        cmd_tail = ' -x {0} -y {1} -W {2} -H {3} "{4}" -'.format(int(point_x),
                                                                 int(point_y),
                                                                 int(width),
                                                                 int(height),
                                                                 self.pdf_file_path)
        command = cmd_ext + cmd_page_params + cmd_tail
        return subprocess.check_output(command, shell=True)

    def generate_text_data(self, row):
        '''Generate Text features for a given block.
        '''
        point_x = (row['left'] * self.horizontal_ratio)
        point_y = (row['top'] * self.vertical_ratio)
        width = (row['width'] * self.horizontal_ratio) + 5
        height = (row['height'] * self.vertical_ratio) + 5
        text = self.get_text_from_pdf(point_x, point_y, width, height)
        character_count = Counter(text)
        if self.check_text_for_continous_dashes(text):
            row['text'] = text.strip().replace('-', '').replace('\n', '')
        elif character_count['.'] > 0 and character_count['.'] < 3:
            row['text'] = text.strip().replace('-', '').replace('.', '').replace('\n', '')
        else:
            row['text'] = text.strip()
        row['text_length'] = len(row['text'])
        row['possible_row_merger'] = '\n' in row['text']
        text_matched = re.findall(self.TEXT_REGEX, row['text'])
        comma_sep_matcher = re.compile(self.COMMA_SEP_REGEX)
        row['comma_separated_numbers_present'] = comma_sep_matcher.match(row['text'].replace('\n', ' ')) is not None
        row['is_text'] = len(text_matched) > 0
        try:
            row['number'] = int(row['text'].replace(',', ''))
        except:
            row['number'] = None
        return row

    def get_processed_blocks(self, block_stats):
        '''
        Apply the list of post processors passed.
        '''
        processed_block_stats = block_stats
        for func in self.post_processors:
            processed_block_stats = func(processed_block_stats)
        return processed_block_stats

    def generate(self):
        '''Extract text based features from each block.

        Returns:
            A Dataframe with each row as block and text based features.
        '''
        block_stats = self.extract_block_stats()
        # Check for blank page
        if len(block_stats.index) > 3:
            block_stats_with_text_data = block_stats.apply(self.generate_text_data, axis=1)
            return self.get_processed_blocks(block_stats_with_text_data)
        return block_stats

# Post processors for image block feature generator

def filter_unwanted_blocks(block_features):
    '''Blank blocks and footer are not desired the blocks that we need to process,
    thus we remove them.
    '''
    # remove blank blocks
    filtered_block_features = block_features[block_features.text_length != 0]
    # remove footer
    return filtered_block_features[filtered_block_features.top < (block_features.top.max() * .95)]


def separate_blocks(block_features):
    '''Some blocks are joined together in the blocks generated we separate them
    into multiple blocks.
    '''
    processed_blocks = pd.DataFrame()
    for index, row in block_features.iterrows():
        splitted_row = []
        if row.possible_row_merger is True:
            for index, value in enumerate(row.text.split('\n')):
                new_row = {}
                for col in row.index:
                    new_row[col] = row[col]
                new_height = row.height // len(row.text.split('\n'))
                new_row['height'] = new_height
                new_row['top'] = row.top + (index * new_height)
                new_row['bottom'] = new_row['top'] + new_height
                new_row['text'] = value
                new_row['possible_row_merger'] = False
                splitted_row.append(new_row)
            processed_blocks = processed_blocks.append(splitted_row)
        else:
            processed_blocks = processed_blocks.append(row)
    return processed_blocks
