# Convert the xlsx data provided by assam govt to a csv file with all the budget codes mapped to their respective names
import pandas as pd
import sqlalchemy
import multiprocessing
import numpy as np
import argparse


SCHEMES = {'CSS': 'Centrally Sponsored Scheme',
          'EAP': 'Externally Aided Projects',
          'EAP-SS': 'Externally Aided Projects-State Share',
          'EE-CS': 'Establishment Expenditure-Central Share',
          'EE-SS': 'Establishmet Expenditure-State Share',
          'EE': 'Establishmet Expenditure',
          'Plan': 'Plan',
          'RIDF-LS': 'Rural Infrastructure Development fund-Loan Share',
          'RIDF-SS': 'Rural Infrastructure Development fund-State Share',
          'SOPD EE-SSA': 'Establishment Expenditure-Six Schedule Area',
          'SOPD-G': 'State Own Priority Scheme-General',
          'SOPD-GSP': 'State Own Priority Scheme-GOI Special Scheme',
          'SOPD-ODS': 'State Own Priority Scheme-Other Development Scheme',
          'SOPD-SCSP': 'State Own Priority Scheme-SCSP',
          'SOPD-SCSP SS': 'State Own Priority Scheme-SCSP State Share',
          'SOPD-SS': 'State Own Priority Scheme-State Share',
          'SOPD-TSP': 'State Own Priority Scheme-TSP',
          'TG-AC': 'Transfer Grants to Autonomous Councils',
          'TG-DC': 'Transfer Grants to Development Councils',
          'TG-EI': 'Transfer Grants to Educational Institutions',
          'TG-FFC': 'Transfer Grants to Finance Commission Grants',
          'TG-IB': 'Transfer Grants to Individual Benefeciaries',
          'TG-PRI': 'Transfer Grants to Panchayat Raj Institutions',
          'TG-SFC': 'Transfer Grants to State Finance Commission Grants',
          'TG-SSA': 'Transfer Grants to Sixth Schedule Areas',
          'TG-UL': 'Transfer Grants to Urban Local Bodies'}


CODES_FOR_AREAS = {'GA': 'General Area',
                   'KN': 'Karbi Anglong Non-entrusted',
                   'NN': 'North Cachar Non-entrusted',
                   'BN': 'Bodoland Non-entrusted',
                   'KE': 'Karbi Anglong Entrusted',
                   'NE': 'North Cachar Entrusted',
                   'BE': 'Bodoland Entrusted'}

COLS = ['#', 'GRANT NUMBER', 'BUDGET ENTITY', 'HEAD OF ACCOUNT',
       'HEAD DESCRIPTION', 'HEAD DESCRIPTION ASSAMESE', 'Major Head',
       'Sub-Major Head', 'Minor Head', 'Sub-Minor Head', 'Detailed Head',
       'Object Head', 'Voucher Head', 'Scheme', 'Area', 'Voted/Charged',
       'ACTUALS 2016-17', 'BUDGET 2017-18', 'REVISED 2017-18', 'BUDGET 2018-19']

def decipher_head_of_account(row, scheme_map, area_map, hard_check=True):
    '''
    Process Head of account of each row to map budget codes to the correct
    definition.
    '''
    head_of_account = row['HEAD OF ACCOUNT']
    hod_split = head_of_account.split('-')
    desc = row['HEAD DESCRIPTION'].split('$')
    row['Major Head'] = desc[0]
    row['Sub-Major Head'] = desc[1]
    row['Minor Head'] = desc[2]
    row['Sub-Minor Head'] = desc[3]
    row['Detailed Head'] = desc[4]
    row['Object Head'] = desc[5]
    row['Voucher Head'] = desc[6]
    scheme_code = '-'.join(hod_split[7:-2])
    area_code = hod_split[-2]
    if hard_check:
        row['Scheme'] = scheme_map[scheme_code]
        row['Area'] = area_map[area_code]
    else:
        if scheme_code in scheme_map:
            row['Scheme'] = scheme_map[scheme_code]
        else:
            row['Scheme'] = scheme_code
        if area_code in area_map:
            row['Area'] = area_map[area_code]
        else:
            row['Area'] = area_code
    row['Voted/Charged'] = 'Charged' if hod_split[-1] == 'C' else 'Voted'
    return row

# multiprocessing for some speed boost
def _apply_df(args):
    df, func, kwargs = args
    return df.apply(func, **kwargs)

def apply_by_multiprocessing(df, func, **kwargs):
    workers = kwargs.pop('workers')
    pool = multiprocessing.Pool(processes=workers)
    result = pool.map(_apply_df, [(d, func, kwargs)
            for d in np.array_split(df, workers)])
    pool.close()
    return pd.concat(list(result))

def set_columns(data):
    '''
    The data file is expected to have first row as nans.
    This function handles the nan row and assigns the right columns.
    '''
    data.columns = data.iloc[1]
    data.drop([0,1], axis=0, inplace=True)
    return data

def save_to_sqlite(o, combined_data):
    '''
    Save the combined data to sqlite file.
    Args:
        o (str): output file name.
    Return:
        True if sqlite file saved else raise error.
    '''
    engine = sqlalchemy.create_engine('sqlite:///{}'.format(o))
    combined_data.to_sql(name='budget_2018_19', if_exists='replace', con=engine, chunksize=10000)
    return True

def process_file(budget_filepath):
    '''
    Process the budget file and generate a processed dataframe
    '''
    data = set_columns(pd.read_excel(budget_filepath))
    assam_processed_data = apply_by_multiprocessing(data,
                                                    decipher_head_of_account,
                                                    args=[SCHEMES, CODES_FOR_AREAS],
                                                    axis=1,
                                                    workers=4)
    return assam_processed_data

def generate_assam_processed_data(budget_filepath, csv=True, sqlite=True):
    '''
    Generate the processed budeget data.

    Args:-
        budget_filepath (str): The file path from where to pick the assam budget file.
        csv (bool:default=True): A boolean flag to generate csv file.
        sqlite (bool:default=True): A boolean flag to generate sqlite db.
    '''
    data = process_file(budget_filepath)
    if csv:
        data.to_csv('assam_processed_budget.csv', index=False)
    if sqlite:
        save_to_sqlite('assam_processed_budget.sqlite', data)


if  __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("xlsx_file",
                        help="The input budget xlsx file to be processed.",
                        type=str)
    parser.add_argument("--csv",
                        help="Flag to generate csv file, default value:True.",
                        default=True)
    parser.add_argument("--sqlite",
                        help="Flag to generate sqlite file, default value:True.",
                        default=True)
    args = parser.parse_args()
    generate_assam_processed_data(args.xlsx_file, args.csv, args.sqlite)
