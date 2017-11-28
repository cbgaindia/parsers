Table Extraction Using Blocks
-----------------------------

Goal
====

The goal is to convert images of tables without table boundaries defining column or row separation into csv's of a particular format that can be uplodaded to OBI's data platform. 


Data
====

WestBengal Demand Drafts https://openbudgetsindia.org/dataset?q=west+bengal


Description
===========

Convert Text into blocks and then extract information from blocks which can be used to classify each block as :-

    - Header
    - Number
    - Grouping
    - Summary
    - Title
    - NaN
