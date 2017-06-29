## Notes

Alternative Technique - 1
http://answers.opencv.org/question/63847/how-to-extract-tables-from-an-image/

The technique assumes that there are lines to be detected in between thus its not as robust as we want it to be.


This is turning out to be a bigger reaserch topic then expected, under the topic of table structure recognition and it happens there was a competition held by ICDAR in 2013  for the same, here are a useful links : -

1. [Table Structure Recognition Based On Robust Block Segmentation](https://www.dfki.uni-kl.de/~kieni/publications/spie98.pdf), [Summary](https://www.dfki.uni-kl.de/~kieni/publications/DLIA99.pdf) - This is similar to what I had in mind.
2. [Tamirhassan's page on ICDAR-2013 competition](http://www.tamirhassan.com/competition/dataset-tools.html (Some researcher's website containing ICDAR-2013 info)
3. [Detecting Table Region in PDF Documents Using Distant Supervision (arxiv)](https://arxiv.org/pdf/1506.08891.pdf)
4. [Table Extraction from Document Images using Fixed Point Model(IIT Delhi!!)](http://www.cse.iitd.ernet.in/~sumantra/publications/icvgip14_table.pdf)


Completely Uneccesary link http://rrc.cvc.uab.es/?com=introduction

Papers on Evaluation, might become useful :-
1. http://www.jdl.ac.cn/doc/2011/2011122317595539031_icdar2011.pdf
2. http://www.orsigiorgio.net/wp-content/papercite-data/pdf/gho*12.pdf

An overview of the problem statement [DAR/Document Analysis](file:///home/jayant/Downloads/9783540762799-c1.pdf),Includes datasets and basic termonology definitions.

Random short read http://www.academicscience.co.in/admin/resources/project/paper/f201503061425662933.pdf

CNN Based approach, not directly related but may be some starting thoughts on how to use CNN https://pdfs.semanticscholar.org/3b57/85ca3c29c963ae396c2f94ba1a805c787cc8.pdf


Another Idea, Use CNN to generate the Masks some material found here :-
1. [Convolutional Feature Masking for Joint Object and Stuff Segmentation](https://arxiv.org/abs/1412.1283)
2. [Fully Convolutional Networks for Semantic Segmentation](http://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/Long_Fully_Convolutional_Networks_2015_CVPR_paper.pdf)



## Summary of Table Structure Recognition Based on Robust Block Segementation (T- Recs)

The Paper talks about :-
1. Segmentation of table images .i.e. identifying textual units such as cells inside a table
2. Analysis of the segmented blocks to detect the higher structure and aggregation. Logical labeling or Layout/Structural analysis.

Keywords to look at :-

     1. White space Density Graph

#### Central Idea
Rather then looking for separators, identify words that belong to the same logical unit thus building structures with a bottom up approach.

#### Process
It assumes that the detection of text is already done and works on that data.

1. Clustering Words into Blocks

       1. Find a word that is not marked.
       2. Initiate a new block.
       3. add the word to the block and mark it as explored.
       4. Examine all horizontally overlapping words, in the previous and the next line.
       5. For each examined word repeat 3,4,5.
       6. If no more overlapping words found, start with 1.
       7. If no more unmarked words left, stop.

2. Post processing
The above clustering is prone to errors thus the major part of this paper is the post processing they do.

       1. Classification of each block into type 1 and type 2, type 1 being blocks with a single word.
       2. Reclustering Of Wrongly Isolated Blocks (Only on block type 2)
       3. Isolation of merged columns (Only on block type 2)
       4. ...
       ....
**Read the paper, its an easy read.**

The main Idea is to use Words to detect blocks and then do a post processing to get a cleaner set. Now Use the Blocks to detect rows and columns in a similar manner.


## Summary of Detecting Table Region in PDF Documents Using Distant Supervision (arxiv)

This paper mostly talks about detecting the regions of tables using three types of features :-
    - Layout Based, Normalized Average Margin (NAM)
    - Text Based, POS Tag Distribution and Named Entity Percentage

They also talk about how they have generated the datasets and the architecture of their model, they are using a combination of NaiveBayes, SVM and Logistic Regression with a voting ensemble in the final layer.

Personel Comments: I don't think this is what we are looking for at the moment.
