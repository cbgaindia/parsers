'''Sensitize and combine csvs generated based on major heads and demand draft.
'''
import re
import pandas as pd


def extract_budget_code(particular):
    '''
    Extract Budget Code from
    '''
    if particular.split('-')[0].strip().isdigit() > 0:
        return '[' + particular.split('-')[0].strip() + ']'
    return None


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

def combine_tables(tables):
    '''
    Combine all files under the same demand no and major head into 1
    '''
    for idx, group in tables.groupby(['demand_no', 'major_head']):
        files = group.filename.tolist()
        combined_csv_filename = 'demand_no_{0}_major_head_{1}_detailed.csv'.format(idx[0], idx[1])
        ddg_df = pd.DataFrame()
        for csv_file_name in files:
            print(csv_file_name)
            table_df = pd.read_csv(csv_file_name, sep=';').dropna(axis=1)
            cols = [col for col in table_df.columns if col is not None]
            table_df = table_df[cols]
            unknown_cols_map, numeric_cols_map = detect_cols(cols, table_df)
            table_df.rename(columns=unknown_cols_map, inplace=True)
            table_df.rename(columns=numeric_cols_map, inplace=True)
            if 'Voted/Charged' not in table_df.columns:
                table_df['Voted/Charged'] = ''
            if 'Particulars' not in table_df.columns:
                table_df['Particulars'] = ''
            table_df['Budget Code'] = table_df['Particulars'].apply(extract_budget_code)
            table_df = table_df.apply(reposition_total, axis=1)
            if 'extra' in table_df.columns:
                table_df.drop('extra', inplace=True, axis=1)
            numeric_cols = ['Actuals, 2015-2016 Rs', 'Budget Estimate, 2016-2017 Rs',
                            'Revised Estimate, 2016-2017 Rs', 'Budget Estimate, 2017-2018 Rs']
            for col in numeric_cols:
                if col not in table_df.columns:
                    table_df[col] = ''
            print(table_df.columns)
            ddg_df = pd.concat([ddg_df, table_df[COLS_ORDER]])
        ddg_df.to_csv(combined_csv_filename, sep=',', index=False, columns=COLS_ORDER)
        print(combined_csv_filename)
    return True

