# keyword-matcher

Keyword/lexical matching baseline: score input text against SFIA skill and
level descriptions using term overlap (TF-IDF/BM25 or similar) and return the
best skills.

Not implemented yet — directory and interface reserved.

Approach: BM25, per:

- Robertson, S. and Zaragoza, H. (2009). "The Probabilistic Relevance
  Framework: BM25 and Beyond." Foundations and Trends in Information
  Retrieval, 3(4), 333-389. https://doi.org/10.1561/1500000019
- Person-job matching precedent: "A Person-job Matching Method Based on
  BM25 and Pre-trained Language Model." Proceedings of the 2023 6th
  International Conference on Machine Learning and Natural Language
  Processing. https://doi.org/10.1145/3639479.3639494
