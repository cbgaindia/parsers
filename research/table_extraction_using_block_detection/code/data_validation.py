import re
import json
from goodtables import validate, check


@check('missing-budget-code', type='custom', context='body')
def missing_budget_code(errors, cells, row_number):
    '''
    Check for missing budget codes where particulars are present.
    '''
    required_cells = {cell['header']: cell['value'] for cell in
                      cells if cell['header'] in ['Budget Code',
                                                  'Particulars']}
    budget_code = required_cells['Budget Code'].strip('[').strip(']')
    particulars = required_cells['Particulars'].strip()
    # check if particulars start with a number
    if len(re.findall(r'^\d', particulars)) > 0:
        # budget code should not be empty and should be part of particulars
        if len(budget_code) == 0 or budget_code not in particulars:
            errors.append({
                'code': 'Minor - Budget Code',
                'message': 'Budget Code missing for the particulars',
                'row-number': row_number,
                'column-number': 1,
            })


@check('numbers-only', type='custom', context='body')
def numbers_only(errors, cells, row_number):
    '''
    Check if there are numbers only in the Numeric Columns.
    '''
    number_cells = [cell for cell in cells if 'Rs' in cell['header']]
    for number_cell in number_cells:
        # check if any text value came into the number columns
        if len(re.findall(r'[a-zA-Z]', number_cell['value'])) > 0:
            errors.append({
                'code': 'Major - Number Columns',
                'message': 'Text present in Number Columns',
                'row-number': row_number,
                'column-number': number_cell['number'],
            })


@check('header-count', type='custom', context='head')
def header_count(errors, cells, row_number):
    '''
    Check the number of numeric and categoricual headers.
    '''
    numeric_headers = [cell['header'] for cell in cells if 'Rs' in cell['header']]
    categorical_headers = [cell['header'] for cell in cells if 'Rs' not in cell['header']]
    if len(numeric_headers) != 4 or len(categorical_headers) != 3:
        errors.append({
            'code': 'Major - Missing Headers',
            'message': 'The number of expected columns is less',
            'row-number': row_number,
            'column-number': 'N/A'
        })


@check('categorical-headers', type='custom', context='head')
def categorical_headers_check(errors, cells, row_number):
    '''
    Check if we have all the categorical columns
    '''
    categorical_headers = [cell['header'] for cell in cells if 'Rs' not in cell['header']]
    fixed_categorical_headers = ['Budget Code', 'Particulars', 'Voted/Charged']
    diff = set(categorical_headers) - set(fixed_categorical_headers)
    if len(diff) > 0:
        errors.append({
            'code': 'Major - Missing Categorical Columns',
            'message': 'Missing either of the fixed columns: {0}'.format(fixed_categorical_headers),
            'row-number': row_number,
            'column-number': 'N/A'
        })


def validate_demand_drafts(csv_files):
    '''
    Run goodtable's validate on a list of dicts containing the csv paths. The checks are
    specific to demand drafts.
    
    Args:
        - csv_files(list:`[{'source': filename}]`): A list of `dicts`
            containing csv file paths 
    
    Returns:
        True if there aren't any errors in the data validation False if there
        are errors. The report is dumped in 'validation_report.json' for
        evaluation.
    '''
    report = validate(csv_files, checks=['numbers-only', 'missing-budget-code',
                                         'missing-header', 'header-count',
                                         'categorical-headers', 'duplicate-header'],
                      preset='nested', table_limit=len(csv_files))
    json.dump(report, 'validation_report.json', indent=4, separators=(',', ': '))
    if report['error_count'] > 0:
        return False
    return True
