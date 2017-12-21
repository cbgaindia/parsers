'''Implementation to convert labelled blocks to csv.
'''
import re
import pandas as pd


class BlocksToCSV(object):
    '''Convert blocks with labels to a csv.
    '''
    DEFAULT_HEADERS = 'Actuals, 2013-2014 Rs;Budget Estimate, 2015-2016 Rs;Revised Estimate, 2015-2016 Rs;Budget Estimate, 2016-2017 Rs;'
    COLUMN_COUNT = 6

    def __init__(self, img, block_features, page_num, target_folder):
        self.img = img
        self.block_features = block_features
        self.page_num = page_num
        self.target_folder = target_folder
        self.rows = []
        self.cols = []

    def find_rows(self, block_features):
        '''
        Figure out the points where rows start and end.

        1. Headers would be the starting point. Bottom of the headers
        2. Each cell value will be separated by a row.
        '''
        rows = []
        if 'header' in block_features.label.unique():
            rows.extend(block_features[block_features['label'] ==
                                       'header'].aggregate({'top': min,
                                                            'bottom': max}).values.flatten())
        else:
            # Incase header is not present add the starting point.
            rows.extend(block_features.aggregate({'top':min}).values.flatten())
        if 'number_values' in block_features.label.unique():
            rows.extend(block_features[block_features['label'] ==
                                       'number_values']['bottom'].unique())
        return rows

    def get_marked_rows(self, block_features):
        '''Mark each block with a row index representing in which row does the
        block lie in.

        Args:
            - block_features (obj:`pd.DataFrame`): A dataframe contatining blocks
            with text and geometrical features.

        Return:
            A Dataframe with `row_index` column. 
        '''
        for table in block_features.table.unique():
            table_block_features = block_features[block_features.table == table]
            rows = self.find_rows(table_block_features)
            self.rows = rows
            combined_rows = sorted(rows +
                                   table_block_features[pd.isnull(table_block_features.label)].
                                   bottom.unique().tolist())
            for index, row_start in enumerate(combined_rows[:-1]):
                row_end = combined_rows[index + 1]
                block_features.loc[((block_features.top.between(row_start, row_end)) &
                                    (block_features.table == table) &
                                    (block_features.label != 'title')), 'row_index'] = index
        return block_features

    def _get_col_feature_count(self, row, table_rows):
        '''Get the number of blocks between last column and the given column in
        a given row.
        '''
        features = table_rows[pd.notnull(table_rows['row_index'])]
        features_in_col = features[features.left.between(row['last_col'], row['cols'] - 5)]
        return len(features_in_col.index)

    def filter_possible_cols(self, cols, table_start, table_end,
                             table_rows, dark_pixel_threshold=300):
        '''
        Figure out possible columns of the table.

        Args:
            - cols (list:`float`): A list of possible column separators.
            - table_start (float): Starting boundary of the table.
            - table_end (float): Ending boundary of the table.
            - table_rows (obj:`pd.DataFrame`): A dataframe containing blocks of
            the table being processed.
            - dark_pixel_threshold (int): A threshold for dark pixel count of a
            column line above which the column line will be removed from the
            list of possible cols.

        Returns:
            A lit of column points that can be extended to make lines.
        '''
        columns_df = pd.DataFrame({'cols': cols}).sort_values(by='cols')
        columns_df['dark_pixel_count'] = columns_df.cols.apply(lambda x: (
            self.img[table_start:table_end, int(x)] < 255).sum())
        columns_df['next_diff'] = columns_df.cols.shift(-1) - columns_df.cols
        columns_df['next_diff'] = columns_df['next_diff'].fillna(1000)
        columns_df['last_col'] = columns_df.cols.shift(1)
        columns_df['last_col'].fillna(135, inplace=True)
        # Check Dark Pixel Count
        filtered_columns_df = columns_df[columns_df['dark_pixel_count'] < dark_pixel_threshold]
        # Threshold from where to start looking for columns
        filtered_columns_df = filtered_columns_df[filtered_columns_df['cols'] > 300]
        # Filter out Columns that do not have any data.
        filtered_columns_df['feature_count'] = filtered_columns_df.apply(self._get_col_feature_count,
                                                                         axis=1,
                                                                         args=[table_rows])
        filtered_columns_df = filtered_columns_df[filtered_columns_df['feature_count'] > 0]
        return filtered_columns_df.cols.tolist()

    def mark_cols(self, features, table_cols, table):
        '''
        Assign each block a column index.

        Args:
            - features (obj:`pd.DataFrame`): Dataframe containing the blocks
            with their features.
            - table_cols (list:`floats`): list of filtered table cols.
            - table (int): The index of the table which we are processing.

        Returns:
            A dataframe with `col_index` for each block along with its
            features.
        '''
        table_rows = features[features.table == table]
        for index, col_start in enumerate(table_cols[:-1]):
            col_end = table_cols[index + 1]
            row_index_count = features[(features.left.between(col_start, col_end) &
                                        (features.table == table))]['row_index'].value_counts()
            overlaps = row_index_count[row_index_count > 1].index
            if len(overlaps) > 0 and index > 0:
                overlapping_features = features[(features.left.between(col_start, col_end) &
                                                 (features.table == table) &
                                                 (features.row_index.isin(overlaps)))]
                overlapping_separating_cols = overlapping_features.groupby('row_index')['right'].min().unique().tolist()
                new_table_cols = (table_cols[:index + 1] +
                                  overlapping_separating_cols +
                                  table_cols[index + 1:])
                new_table_cols = [int(x) for x in new_table_cols]
                table_start = min(new_table_cols)
                table_end = max(new_table_cols) + 1
                cols = self.filter_possible_cols(new_table_cols, table_start, table_end, table_rows)
                if table_cols != cols:
                    return self.mark_cols(features, cols, table)
            features.loc[(features.left.between(col_start, col_end) &
                          (features.table == table)), 'col_index'] = index
        return features

    def get_possible_cols(self, table_rows):
        '''Get a list of all possible columns based on the blocks in a table.

        Args:
            table_rows (obj:`pd.DataFrame`): Blocks of a particular table.

        Returns:
            A lits of possible columns.
        '''
        col_per_row = table_rows.groupby('row_index')['pos'].count()
        possible_cols = table_rows[table_rows.row_index.isin(col_per_row[col_per_row ==
                                                                         col_per_row.max()]
                                                             .index.tolist())].right.unique()
        return possible_cols

    def get_marked_cols(self, features_with_rows):
        '''Mark all columns from all tables.

        Args:
            - features_with_rows (obj:`pd.DataFrame`): A dataframe containing
            blocks marked with row indices.

        Returns:
            The block features dataframe with `col_index` column.
        '''
        for table in features_with_rows.table.unique():
            table_rows = features_with_rows[features_with_rows.table == table]
            if len(table_rows.row_index.dropna()) == 0:
                continue
            possible_cols = self.get_possible_cols(table_rows)
            v_table_start, v_table_end = table_rows.agg({'top':min, 'bottom': max}).values.flatten()
            h_table_start = table_rows.left.min()
            dark_pixel_threshold = (v_table_end - v_table_start) * 0.3
            cols = self.filter_possible_cols(possible_cols, int(v_table_start),
                                             int(v_table_end), table_rows,
                                             dark_pixel_threshold)
            table_cols = [h_table_start] + sorted(cols)
            features_with_rows = self.mark_cols(features_with_rows, table_cols, table)
        return features_with_rows

    def get_features_with_rows_and_cols(self):
        '''Mark rows and columns of all the blocks based on the features and
        labels.
        '''
        block_features_with_rows = self.get_marked_rows(self.block_features)
        return self.get_marked_cols(block_features_with_rows)

    def extract_term(self, titles, term):
        '''
        Extract Numbers based on particular term if present.
        '''
        filtered_titles = titles[titles.text.str.lower().str.contains(term)]
        if len(filtered_titles) < 1:
            return None
        term_text = filtered_titles.text.iloc[0]
        return ' '.join(re.findall(r'\d+', term_text))

    def detect_term(self, titles, term):
        '''
        Detect a term in title
        '''
        filtered_titles = titles[titles.text.str.lower().str.contains(term)]
        if len(filtered_titles) > 0:
            return True
        return False

    def write_to_csv(self):
        '''Detect Layout of the blocks and convert them into a csv file.
        '''
        block_features = self.get_features_with_rows_and_cols()
        block_features.to_csv('{0}/log_block_features/{1}_table_row_col_indices.csv'.format(self.target_folder,
                                                                                            self.page_num),
                              index=False)
        tables = []
        for table_no in block_features.table.unique():
            # Retain/Extract the following features for table joining
            #    - Page No
            #    - Table No
            #    - Major Head
            #    - Demand No (if present)
            table_features = block_features[block_features.table == table_no]
            titles = table_features[table_features.label == 'title']
            demand_no = self.extract_term(titles, 'demand no')
            major_head = self.extract_term(titles, 'major head')
            head_of_account = self.extract_term(titles, 'head of account')
            abstract = self.detect_term(titles, 'abstract')
            detailed = self.detect_term(titles, 'detailed')
            detailed_account_no = self.extract_term(titles, 'detailed account no')
            filename = '{0}/{1}_{2}.csv'.format(self.target_folder, self.page_num, table_no)
            tables.append({'page_no': self.page_num,
                           'table': table_no,
                           'demand_no': demand_no,
                           'major_head': major_head,
                           'head_of_account': head_of_account,
                           'detailed': detailed,
                           'abstract': abstract,
                           'detailed_account_no': detailed_account_no,
                           'filename': filename})
            if pd.notnull(table_features.col_index.max()):
                max_col = int(table_features.col_index.max()) + 1
            else:
                max_col = 0
            with open(filename, 'w') as csv_file:
                # for each row write a line
                if 'header' not in table_features.label.unique():
                    number_of_default_headers = len(self.DEFAULT_HEADERS.split(';')) - 1
                    if 'number_values' in table_features.label.unique():
                        headers_row = ';' * (max_col - number_of_default_headers)
                        headers_row += self.DEFAULT_HEADERS
                    else:
                        headers_row = ';;' + self.DEFAULT_HEADERS
                    csv_file.write(headers_row)
                    csv_file.write('\n')
                for _, group in table_features.sort_values('top').groupby('row_index'):
                    row = ''
                    for column_index in range(max_col):
                        value = group[group.col_index == column_index]
                        if len(value.index) == 0:
                            row += ' ;'
                        else:
                            row += value.text.iloc[0] + ';'
                    csv_file.write(row)
                    csv_file.write('\n')
        return tables
