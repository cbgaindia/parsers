## Notes

Alternative Technique - 1
http://answers.opencv.org/question/63847/how-to-extract-tables-from-an-image/
The technique assumes that there are lines to be detected in between thus its not as robust as we want it to be.


This is turning out to be a bigger reaserch topic then expected, under the topic of table structure recognition and it happens there was a competition held by ICDAR in 2013  for the same, here are a useful links : -

To Read List : -
  - [x] [Table Structure Recognition Based On Robust Block Segmentation](https://www.dfki.uni-kl.de/~kieni/publications/spie98.pdf), [Summary](https://www.dfki.uni-kl.de/~kieni/publications/DLIA99.pdf) - This is similar to what I had in mind.
  - [x] [Detecting Table Region in PDF Documents Using Distant Supervision (arxiv)](https://arxiv.org/pdf/1506.08891.pdf)
  - [x] [Table Extraction from Document Images using Fixed Point Model(IIT Delhi!!)](http://www.cse.iitd.ernet.in/~sumantra/publications/icvgip14_table.pdf)
  - [ ] [ANN for Document Analysis and Recognition](https://pdfs.semanticscholar.org/b02b/5c1c35c0897ed7f399df2cff8aee107a0d98.pdf)
  - [ ] [Table Detection via Probability Optimization](http://gsl.lab.asu.edu/doc/tabledas02.pdf)

Note Worthy Links :-
  1. [Tamirhassan's page on ICDAR-2013 competition](http://www.tamirhassan.com/competition/dataset-tools.html (Some researcher's website containing ICDAR-2013 info)
  2. http://rrc.cvc.uab.es/?com=introduction
  3. http://www.academicscience.co.in/admin/resources/project/paper/f201503061425662933.pdf

Bigger Reads :-
  An overview of the problem statement [DAR/Document Analysis](http://www.springer.com/cda/content/document/cda_downloaddocument/9783540762799-c1.pdf?SGWID=0-0-45-480217-p173779118),Includes datasets and basic termonology definitions.

Papers on Evaluation of icdar 2013 data, might become useful :-
1. http://www.jdl.ac.cn/doc/2011/2011122317595539031_icdar2011.pdf
2. http://www.orsigiorgio.net/wp-content/papercite-data/pdf/gho*12.pdf

CNN Based approach, not directly related but may be some starting thoughts on how to use CNN https://pdfs.semanticscholar.org/3b57/85ca3c29c963ae396c2f94ba1a805c787cc8.pdf


An Idea, Use CNN to generate the Masks some material found here :-
1. [Convolutional Feature Masking for Joint Object and Stuff Segmentation](https://arxiv.org/abs/1412.1283)
2. [Fully Convolutional Networks for Semantic Segmentation](http://www.cv-foundation.org/openaccess/content_cvpr_2015/papers/Long_Fully_Convolutional_Networks_2015_CVPR_paper.pdf)


# Summaries

## [1. Table Structure Recognition Based on Robust Block Segementation (T- Recs)](https://www.dfki.uni-kl.de/~kieni/publications/spie98.pdf)

### Description
The Paper talks about :-
1. Segmentation of table images .i.e. identifying textual units such as cells inside a table
2. Analysis of the segmented blocks to detect the higher structure and aggregation. Logical labeling or Layout/Structural analysis.

Keywords to look at :-

     1. White space Density Graph

#### Central Idea
Rather then looking for separators, identify words that belong to the same logical unit thus building structures with a bottom up approach.

### Details

The paper doesn't talk about the data they have used, but rather explains how T-Recs works.

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

### Personal Comments
The later part where the paper claims to really shine are the post processing rule based processing, which I am not super comfortable with. I would prefer completely trainable and scalable pipeline.


## [2. Summary of Detecting Table Region in PDF Documents Using Distant Supervision (arxiv)](https://arxiv.org/pdf/1506.08891.pdf)

### Description
This paper mostly talks about detecting the regions of tables using three types of features :-
    - Layout Based, Normalized Average Margin (NAM)
    - Text Based, POS Tag Distribution and Named Entity Percentage

They also talk about how they have generated the datasets and the architecture of their model, they are using a combination of NaiveBayes, SVM and Logistic Regression with a voting ensemble in the final layer.

### Personel Comments
I don't think this is what we are looking for at the moment, though this can serve as one part of the pipeline.

**TODO: Details to be covered if we decide to dig deeper into this.**

## [3. Table Extraction from Document Images using Fixed Point Model(IIT Delhi!!)](http://www.cse.iitd.ernet.in/~sumantra/publications/icvgip14_table.pdf)

### Description

The authors have treated table detection as a Classification problem, specifically into `table-header`, `table-trailer`,
`table-cell`, `non-table`. They also talk about a lot of older processes that exists and which ones they are inspired by, thus its a good read to get some context of other methods. Also, this is the first paper I have read so far that talks about a complete learning based pipeline rather then rule based. They are also comparing their results with other methods.


### Data Sets Used for testing and training : -
   - UW-III dataset
   - UNLV dataset
   - Their own dataset

### Process
The process involves 4 stages

#### 1. Block Extraction
This is also the pre processing stage.
    - The images are converted into grey scale and binarized.
    - Image segmentation into text and graphic regions using leptonica library by bloomberg.
    - A morphological closing operation is performed on the text regions
    The above operations forms text blobs.

#### 2. Feature Extraction / Feature Set
- Apearence Features
- Contextual Features
- Identifying White Space Separators (thin/thick etc.)
- Identifying Horizontal and Vertical Lines

#### 3. Neighbourhood Estimation
Inter Relationship Features between blocks, they are checking 13 neibhours for this feature.

#### 4. Block Labeling
The Final step of classifying the blocks, they are using Kernel Logistic Regression (KLR) with RBF kernel as the contextual prediction function and SVM with L1 regularization as the classifier.

### Personal Comments
I like the approach, the feature generation etc steps are quite well defined, but I feel there might be more digging required into the cited papers to build a proper understanding for a few things (mostly because it sounds simple while reading the paper, which I am pretty sure of it wouldn't be.).

Other then that I think we might be able to use the same data preparation of text blobs as an input to a CNN.
