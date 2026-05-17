# congressional-alpha

![Status: In progress](https://img.shields.io/badge/status-in%20progress-blue)

A fully local data, NLP, and backtesting pipeline for analyzing whether U.S. senator stock disclosures contain tradeable alpha.

## Data Notes

Yahoo Finance news coverage is recent and uneven by ticker. Older Senate trades will often have no matching Yahoo headline history, so downstream analysis must treat news/NLP coverage as sparse rather than complete.
