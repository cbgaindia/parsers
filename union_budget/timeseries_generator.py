import argparse
import glob
import logging
from logging.config import fileConfig
import pandas as pd

fileConfig('parsers/logging_config.ini')
logger = logging.getLogger()

class TimeseriesGenerator():
    def generate_timeseries_file(self, input_dir, output_dir, filename):
        files = glob.glob("%s/*/Budget at a Glance/%s.csv" % (input_dir, filename)) 
        files.sort()
        timeseries_df = None
        for file_name in files:
            if type(timeseries_df).__module__ != "pandas.core.frame":
                timeseries_df = pd.read_csv(file_name)
            else:
                print(file_name)
                file_df = pd.read_csv(file_name)
                if len(timeseries_df) == len(file_df):
                    timeseries_df.insert(len(timeseries_df.columns)-1, file_df.columns[-4], file_df[file_df.columns[-4]].tolist())
                    timeseries_df.insert(len(timeseries_df.columns), file_df.columns[-2], file_df[file_df.columns[-2]].tolist())
                    timeseries_df.insert(len(timeseries_df.columns), file_df.columns[-1], file_df[file_df.columns[-1]].tolist())
        timeseries_df.to_csv("%s/%s.csv" % (output_dir, filename), index=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generates timeseries CSV files from Combined Budget PDF Document(IPFS)")
    parser.add_argument("input_dir", help="Input Dir with yearwise IPFS data folders")
    parser.add_argument("output_dir", help="Output filepath for budget document")
    parser.add_argument("filename", help="Filename to pick")
    args = parser.parse_args()
    obj = TimeseriesGenerator()
    if not args.input_dir or not args.output_dir or not args.filename: 
        print("Please input directory to begin CSV extraction")
    else:
        obj.generate_timeseries_file(args.input_dir, args.output_dir, args.filename)
