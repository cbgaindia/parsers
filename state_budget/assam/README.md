# Assam Budget Parser

This parser processes the xslx file provided by Assam Government and maps all the budget codes mentioned in the "Head of Description" to its respective description.

To use the script run

```python
python scripts/generate_processed_data.py path/to/the/xlsx/file
```

The above script will generate a csv and a sqlite file that can be consumed.

# Structure

**Exploration** contains the ipython notebooks used to do trials done for processing of the data file shared.

**scripts** contains the final code script that can be directly used to process the data file.
