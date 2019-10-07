'''Sensitize and combine csvs generated based on major heads and demand draft.
'''
import re
import pandas as pd
from collections import Counter


def extract_budget_code(particular):
    '''
    Extract Budget Code from particulars
    '''
    if isinstance(particular, basestring) and particular.split('-')[0].strip().isdigit() > 0:
        return '[' + particular.split('-')[0].strip() + ']'
    return ''


class Renamer():
    '''A class to rename duplicate columns in a dataframe.

    Args:
        - columns(list): a list of column names

    Returns:
        Separate column names for columns that are duplicate
        in a dataframe.
    '''
    def __init__(self, columns):
        self.counter = Counter(columns)

    def __call__(self, col_name):
        if self.counter[col_name] > 1:
            self.counter[col_name] += 1
            return "%s_%d" % (col_name, self.counter[col_name])
        else:
            return col_name


def deduplicate_columns(data):
    '''
    The detection of column types sometimes mark 2 columns as the same.
    To handle such scenarios we combine the columns with string.

    Args:
        - data(object:`pd.DataFrame`): csv being processed loaded as dataframe.

    Returns:
        A pandas dataframe with no duplicates column.
    '''
    col_counter = Counter(data.columns)
    data.rename(columns=Renamer(data.columns), inplace=True)
    for col_name in [col for col in col_counter if col_counter[col] > 1]:
        merge_cols = [col for col in data.columns if '{0}_'.format(col_name) in
                      col]
        data[col_name] = ''
        for merge_col in merge_cols:
            data[col_name] = data[col_name].str.cat(data[merge_col].astype(str))
    return data


def reposition_total(row):
    '''
    We want to push Total into the Particulars column if found in 'voted/charged'
    '''
    if 'Voted/Charged' in row and 'total' in row['Voted/Charged'].lower():
        if len(row['Particulars'].strip()) == 0:
            row['Particulars'] = row['Voted/Charged']
            row['Voted/Charged'] = ''
    if 'extra' in row and len(row['Particulars'].strip()) == 0:
        row['Particulars'] = row['extra']
    return row


def detect_cols(cols, table_df):
    '''Detect the required columns :
        - Particulars
        - Extra
        - Voted/Charged

    Args:
        - cols (list:`string`): list of column names
        - table_df (obj:`pd.DataFrame`): csv being processed loaded as dataframe

    Returns:
        two `dict` containg mapping of detected columns and numerical columns.
    '''
    unknown_cols_map = {col:None for col in cols if 'Rs' not in col}
    numeric_cols_map = {col:col.replace('.', '') for col in cols if 'Rs' in col}
    for _, col in enumerate(unknown_cols_map.keys()):
        particulars = table_df[col].apply(lambda x: len(re.findall(PARTICULARS_MATCHER, x))).sum()
        voted_and_charged = table_df[col].str.contains('Voted').sum() + table_df[col].str.contains('Charged').sum()
        total = table_df[col].str.contains('Total').sum()
        if particulars > 0:
            unknown_cols_map[col] = 'Particulars'
        elif total > 0 and voted_and_charged == 0:
            unknown_cols_map[col] = 'extra'
        elif voted_and_charged > 0:
            unknown_cols_map[col] = 'Voted/Charged'
    return unknown_cols_map, numeric_cols_map

PARTICULARS_MATCHER = r'^\d+[\s-]+[\w\s\-_]+'
COLS_ORDER = ['Budget Code', 'Particulars', 'Voted/Charged',
              'Actuals, 2015-2016 Rs', 'Budget Estimate, 2016-2017 Rs',
              'Revised Estimate, 2016-2017 Rs', 'Budget Estimate, 2017-2018 Rs']

def combine_tables(tables, target_folder):
    '''
    Combine all files under the same demand no and major head into 1
    '''
    ddg_df = pd.DataFrame()
    grouper = ['demand_no', 'major_head']
    unique_demand_no = tables[pd.notnull(tables.demand_no)].demand_no.unique()
    if len(unique_demand_no) == 0:
        tables.demand_no = 999
    elif len(unique_demand_no) == 1:
        tables.demand_no = unique_demand_no[0]
    for idx, group in tables.groupby(grouper):
        files = group.filename.tolist()
        if len(grouper) == 2:
            combined_csv_filename = '{2}/demand_no_{0}_major_head_{1}_detailed.csv'.format(idx[0],
                                                                                           idx[1],
                                                                                           target_folder)
        else:
            combined_csv_filename = '{2}/demand_no_{0}_major_head_{1}_detailed.csv'.format('-',
                                                                                           idx[0],
                                                                                           target_folder)

        ddg_df = pd.DataFrame()
        for csv_file_name in files:
            print(csv_file_name)
            table_df = pd.read_csv(csv_file_name, sep=';').dropna(axis=1)
            cols = [col for col in table_df.columns if col is not None]
            table_df = table_df[cols]
            unknown_cols_map, numeric_cols_map = detect_cols(cols, table_df)
            table_df.rename(columns=unknown_cols_map, inplace=True)
            table_df.rename(columns=numeric_cols_map, inplace=True)
            cols = [col for col in table_df.columns if col is not None]
            table_df = table_df[cols]
            table_df = deduplicate_columns(table_df)
            if 'Voted/Charged' not in table_df.columns:
                table_df['Voted/Charged'] = ''
            if 'Particulars' not in table_df.columns:
                table_df['Particulars'] = ''
            table_df['Budget Code'] = table_df['Particulars'].apply(extract_budget_code)
            table_df = table_df.apply(reposition_total, axis=1)
            if 'extra' in table_df.columns:
                table_df.drop('extra', inplace=True, axis=1)
            numeric_cols = numeric_cols_map.values()
            for col in numeric_cols:
                if col not in table_df.columns:
                    print(col, ' not found in table')
                    table_df[col] = ''
            cols = [col for col in table_df.columns if col is not None]
            table_df = table_df[cols]
            numeric_cols = [col for col in table_df.columns if 'Rs' in col]
            categorical_cols = COLS_ORDER[:3]
            cols_order = categorical_cols + numeric_cols
            ddg_df = pd.concat([ddg_df, table_df[cols_order]])
        ddg_df.to_csv(combined_csv_filename, sep=',', index=False,
                      columns=cols_order)
        print(combined_csv_filename)
    return True

