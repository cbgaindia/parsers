import argparse
import csv
import simplejson

class DataTransformer(object):
    def transform(self, input_file, output_file):
        year_header_map = {}
        output_dict = []
        with open(input_file, 'rb') as in_csv_file:
            csv_reader = csv.reader(in_csv_file, delimiter=',')
            for row in csv_reader:
                if int(csv_reader.line_num) == 1:
                    for col_index in range(1,len(row)):
                        row[col_index] = row[col_index].strip()
                        year = row[col_index].split(" ")[0]
                        budget_type = " ".join(row[col_index].split(" ")[1:])
                        year_header_map[col_index] = {"year" : year, "budget_type" : budget_type}
                else:
                    # Check if the row is empty
                    row_slug = "".join(row[2:])
                    if row_slug.replace(' ', '') == '':
                        continue

                    indicator_dict = {"name": row[1].strip(), "series": []}

                    for col_index in range(2,len(row)):
                        td_value = row[col_index].strip()
                        # Check if the td value is numeric then convert to float
                        if td_value.replace('.', '').isdigit():
                            td_value = float(td_value)

                        budget_type = year_header_map[col_index]["budget_type"]
                        year = year_header_map[col_index]["year"]

                        data_entered = False
                        for budget_dict in indicator_dict["series"]:
                            if "key" in budget_dict and budget_dict["key"] == budget_type:
                                budget_dict["values"].append({"label" : year, "value" : td_value}) 
                                data_entered = True
                                
                        if not data_entered:
                            indicator_dict["series"].append({"key" : budget_type, "values":[{"label" : year, "value" : td_value}]}) 
                    output_dict.append(indicator_dict)
        output_json = simplejson.dumps(output_dict)
        output_file_obj = open(output_file, "w")
        output_file_obj.write(output_json)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Transforms input CSV file into JSON file")
    parser.add_argument("input_file", help="Input CSV filepath")
    parser.add_argument("output_file", help="Output JSON filepath")
    args = parser.parse_args()
    obj = DataTransformer()
    if not args.input_file or not args.output_file: 
        print("Please pass input and output filepaths")
    else:
        obj.transform(args.input_file, args.output_file) 
