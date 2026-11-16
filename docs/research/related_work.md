# Related work and engineering concepts

## Flipkart engineering

- Kumar, “The Science of Unified Ranking: Integrating Ads and Organic Recommendations,” Flipkart Tech Blog, 2025. Describes candidate sourcing, a multi-stage funnel, and unified ranking for a Similar Products widget. It motivates separating candidate generation from ranking; AisleIQ does not reproduce that deployed system. [Article](https://blog.flipkart.tech/the-science-of-unified-ranking-integrating-ads-and-organic-recommendations-8cc24113ef21)
- Sanjanwala, “Multi-Objective Optimisation in Suggestions Ranking @ Flipkart,” Flipkart Tech Blog, 2024. Discusses learning-to-rank suggestions under latency constraints. [Article](https://blog.flipkart.tech/multi-objective-optimisation-in-suggestions-ranking-flipkart-49099b951eae)
- “Addressing Vocabulary Gap in E-commerce Search,” SIGIR 2019. Describes expert-identified query rewrites and vocabulary-gap analysis for Flipkart search. Its internal query logs and judgments are not used here. [Paper](https://cse.iitkgp.ac.in/~pawang/papers/sigir19.pdf)

## Retrieval and ranking

- Robertson and Zaragoza, “The Probabilistic Relevance Framework: BM25 and Beyond,” *Foundations and Trends in Information Retrieval*, 2009. BM25 provides a strong lexical baseline with term-frequency saturation and document-length normalization. [DOI](https://doi.org/10.1561/1500000019)
- Cormack, Clarke and Buettcher, “Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods,” SIGIR 2009. RRF combines ranked lists without pretending their raw scores share a scale. [DOI](https://doi.org/10.1145/1571941.1572114)
- Karpukhin et al., “Dense Passage Retrieval for Open-Domain Question Answering,” EMNLP 2020. Demonstrates bi-encoder dense retrieval as a complementary semantic retrieval approach. Product search has different data and relevance assumptions. [ACL Anthology](https://aclanthology.org/2020.emnlp-main.550/)
- Burges, “From RankNet to LambdaRank to LambdaMART: An Overview,” 2010. LambdaMART optimizes ranking-oriented gradients over query groups and requires defensible graded relevance labels. This repository deliberately does not fit it to the weak synthetic benchmark. [Microsoft Research](https://www.microsoft.com/en-us/research/publication/from-ranknet-to-lambdarank-to-lambdamart-an-overview/)
- Järvelin and Kekäläinen, “Cumulated Gain-Based Evaluation of IR Techniques,” ACM TOIS 2002. nDCG discounts lower-ranked gains and normalizes against an ideal ranking. [DOI](https://doi.org/10.1145/582415.582418)

## Review evidence and explainability

- Mudambi and Schuff, “What Makes a Helpful Online Review?,” *MIS Quarterly*, 2010. Studies review helpfulness and product type; review text contains decision-relevant information beyond star averages. [DOI](https://doi.org/10.2307/20721420)
- Chen et al., “Neural Attentional Rating Regression with Review-Level Explanations,” WWW 2018. Connects review evidence to interpretable recommendation outputs. [DOI](https://doi.org/10.1145/3178876.3186070)
- The cited IIT Bombay survey discusses query-focused comparative summaries and explainable recommendation, but its text’s “Flipkart Q2P” section supplies no data artifact or access instructions. Its dataset statistics are therefore treated as unverified claims, not as a usable dataset. [Survey PDF](https://www.cfilt.iitb.ac.in/resources/surveys/2025/june_cfilt_2025_arnav_anuj_survey_paper.pdf)

## Project design choices

AisleIQ uses BM25 and optionally a CPU sentence-transformer encoder; rank lists are merged with reciprocal rank fusion. Hard price/category constraints run before feature scoring. Review excerpts are copied directly from normalized source rows and retain deterministic IDs. Aspect classification and polarity remain simple rule-based baselines, with explicit missing evidence. The “confidence” value is a heuristic evidence-coverage indicator, not a calibrated probability.
