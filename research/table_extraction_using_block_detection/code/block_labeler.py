class BlockLabeler(object):
    '''Label each block based on some rules.
    '''
    SUMMARY_REGEX = '^[A-za-z]*\sRs\s[0-9,NniIlL]*$'

    def __init__(self, block_features, post_processors=[]):
        self.block_features = block_features
        self.post_processors = post_processors
        if 'label' not in self.block_features.columns:
            self.block_features['label'] = None
    
    def mark_number_cells(self, row, features):
        if (row['comma_separated_numbers_present'] and row['is_text'] == 0) or (row['text'] == '...'):
            row['label'] = 'number_values'
        return row
    
    def mark_header(self, row, features):
        right, top = row.right, row.top
        numbers_below = features[(features.right.between(right - 10, right + 10)) & 
                                 (features.top > top) & 
                                 (features.label == 'number_values')]
        # To avoid groupings getting marked as headers
        numbers_right = features[(features.top.between(top - 10, top + 10)) &
                                (features.right > right) &
                                (features.label == 'number_values')
                               ]
        width_check = row['width'] < 1000
        if len(numbers_below) > 1 and row['label'] != 'number_values' and width_check:
            if len(numbers_right) < 1:
                row['label'] = 'header'
        return row
    
    def mark_probable_headers(self, row, features):
        left, top = row['left'], row['top']
        right, bottom = row['right'], row['bottom']
#         features = features[features.table == row['table']]
        # labels in a radius of 15
        x_pos_axis = features[(features.left.between(right - 10, right + 15)) &
                              (features.label == 'header')]
        x_neg_axis = features[(features.right.between(left - 15, left + 10)) &
                              (features.label == 'header')]
        y_pos_axis = features[(features.bottom.between(top - 20, top + 10)) &
                              (features.label == 'header')]
        y_neg_axis = features[(features.top.between(bottom - 10, bottom + 15)) &
                              (features.label == 'header')]

        if (len(x_pos_axis) + len(x_neg_axis) + len(y_pos_axis) + len(y_neg_axis)) > 0:
            if pd.isnull(row['label']):
                row['label'] = 'header'
        return row

    
    def mark_grouping(self, row, features):
        left, right = row.left, row.right
        top, bottom = row.top, row.bottom
        top_left_check = features[(features.top.between(top - 10, top + 10)) &
                                  (features.left > left) &
                                  (features.label == 'number_values')
                                 ]
        bottom_left_check = features[(features.bottom.between(bottom - 10, bottom + 10)) &
                                  (features.left > left) &
                                  (features.label == 'number_values')
                                 ]
        if len(top_left_check.index) > 0 or len(bottom_left_check.index) > 0:
            if pd.isnull(row['label']):
                row['label'] = 'grouping'
        return row
    
    def mark_title(self, row):
        if (row.is_text == True and 
            row.centroid_x > 1200 and
            row.centroid_x < 1300 and
            pd.isnull(row.label)
           ):
            row['label'] = 'title'
        return row
    
    def mark_summary(self, row):
        if row['is_text'] == True:
            summaries = re.findall(self.SUMMARY_REGEX, row['text'])
            if len(summaries) > 0:
                row['label'] = 'cell_summary'
        return row

    def get_processed_blocks(self, block_features):
        processed_block_feature = block_features
        for func in self.post_processors:
            processed_block_feature = func(processed_block_feature)
        return processed_block_feature
    
    def label(self):
        block_features = self.block_features.apply(self.mark_number_cells, axis=1, args=[self.block_features])
        block_features = block_features.apply(self.mark_header, axis=1, args=[block_features])
        block_features = block_features.apply(self.mark_grouping, axis=1, args=[block_features])
        block_features = block_features.apply(self.mark_title, axis=1)
        block_features = block_features.apply(self.mark_probable_headers, axis=1, args=[block_features])
        return self.get_processed_blocks(block_features.apply(self.mark_summary, axis=1))


# Post Processors for labeler

def check_table_separators(separators, features):
    '''
    For each table separator there should be `number_value` blocks above and
    below it.
    '''
    filtered_separators = []
    if len(separators) > 1:
        #TODO: Handle when separators are more then 1. .i.e. more then 1 table detected.
        return separators

    for separator in separators:
        numbers_above = len(features[(features.top < separator) & (features.label == 'number_values')])
        numbers_below = len(features[(features.top > separator) & (features.label == 'number_values')])
        if numbers_above > 0 and numbers_below > 0:
            filtered_separators.append(separator)
    return filtered_separators

def mark_tables_using_titles(features):
    titles = features[features.label == 'title']
    titles['next_diff'] = titles.top - titles.top.shift(1)
    seperators = titles[titles.next_diff > titles.next_diff.mean()]['top'].tolist()
    begin, end = features.top.min(), features.bottom.max()
    seperators = [begin] + check_table_separators(seperators, features) + [end]
    features['table'] = None
    for index, sep in enumerate(seperators):
        if index > 0:
            table_start, table_end = seperators[index - 1], sep
            features.loc[
                    features['top'].between(table_start, table_end),
                    'table'
                ] = index
    return features


def combine_headers(features):
    """
    1. Combine Headers based on nearby labeled blocks.
    """
    processed_features = pd.DataFrame()
    skip_pos = []
    for index, row in features.iterrows():
        if row['pos'] not in skip_pos:
            nearby_header = features[(features.left.between(row['left'] - row['width'], row['right'])) &
                                     (features.index != index) &
                                     (features.label == 'header') &
                                     (features.table == row['table'])].sort_values('top', ascending=True)
            if len(nearby_header) > 0 and row['label'] == 'header':
                # if mergable create a common label and push the `pos` of
                # the row that is being merged into skip_pos
                row['text'] = row['text'] + ' ' + ' '.join(nearby_header.text.tolist())
                row['text'] = row['text'].replace('\n', ' ')
                row['width'] = max([row['width']] + nearby_header.width.tolist())
                row['height'] = row['height'] + nearby_header.height.sum()
                row['left'] = min(row['left'], nearby_header.left.min())
                row['right'] = row['left'] + row['width']
                row['bottom'] = row['top'] + row['height']
                skip_pos.extend(nearby_header.pos.tolist())
            processed_features = processed_features.append(row)
    return processed_features


def remove_false_headers(features):
    '''
    Unlabel blocks that are marked as headers and are distant from actual headers
    '''
    positions_to_unlabel = []
    for table_no in features.table.unique():
        table_rows = features[features.table == table_no]
        table_headers = features[features.label == 'header']
        table_headers['top_zscore'] = (table_headers.top - table_headers.top.mean()) / table_headers.top.std(ddof=0)
        positions_to_unlabel.extend(table_headers[table_headers.top_zscore > 1]['pos'].values.flatten())
    features.loc[features.pos.isin(positions_to_unlabel), 'label'] = None
    return features

def combine_horizontal(block_features):
    """
    1. Combine Blocks based on their horizontal distance.
    """
    processed_features = pd.DataFrame()
    skip_pos = []
    for index, row in block_features.iterrows():
        if row['pos'] not in skip_pos:
            nearby_labels = block_features[(block_features.left.between(row['left'] - 5, row['right'] + 5)) &
                                           (block_features.top.between(row['top'] -5, row['top'] + 5)) &
                                           (block_features.pos != row['pos'])]
            if len(nearby_labels) > 0 and row['label'] not in ['header', 'number_values']:
                # if mergable create a common label and push the `pos` of
                # the row that is being merged into skip_pos
                row['text'] = row['text'] + ' '.join(nearby_labels.text.tolist())
                row['width'] = row['width'] + nearby_labels.width.sum()
                row['right'] = row['left'] + row['width']
                skip_pos.extend(nearby_labels.pos.tolist())
            processed_features = processed_features.append(row)
    return processed_features


def combine_text_starting_with_lower_case(block_features):
    '''
    Text starting with lower cases and that has no label needs to be combined with the text above.
    '''
    text_with_no_labels = block_features[pd.isnull(block_features.label)]
    text_with_no_labels['text_to_be_merged'] = text_with_no_labels['text'].apply(lambda x: not (x[0].isupper() or x[0].isdigit()))
    for index, row in text_with_no_labels.iterrows():
        print(index, row['text'], row['text_to_be_merged'])
    return block_features
