| Method | Accuracy | Macro-F1 | Unsupported sentences (Flash judge) | Uncited | Retrieval hit | $ / question | Median s | Unsupported (MiniCheck, rejected) |
|---|---|---|---|---|---|---|---|---|
| Plain RAG | 63.8% | 0.580 | 21.8% | 9.4% | 98.2% | $0.0012 | 10 | 44.5% |
| VeritasMed | 63.6% | 0.565 | 14.5% | 3.5% | 98.4% | $0.0105 | 59 | 21.5% |
| Strict-prompt RAG | 51.0% | 0.464 | 8.9% | 2.6% | 98.2% | $0.0016 | 13 | 30.5% |

Paired differences vs VeritasMed (percentage points, 95% bootstrap interval):

- A1-A2: accuracy: +0.2 [-3.6, +4.0]; unsupported_flash: +7.3 [+4.9, +9.6]; bottom_line_unsupported: +21.3 [+16.1, +26.6]; unsupported_minicheck: +23.0 [+20.2, +25.9]
- A5-A2: accuracy: -12.6 [-16.6, -8.4]; unsupported_flash: -5.6 [-7.6, -3.6]; bottom_line_unsupported: -2.4 [-6.7, +2.1]; unsupported_minicheck: +9.0 [+6.3, +11.8]

Bottom line (first sentence) unsupported - uncited or rejected by Flash; exploratory, found after the main analysis:

- Plain RAG: 40.1% of 474 answers
- VeritasMed: 15.8% of 450 answers
- Strict-prompt RAG: 15.1% of 457 answers

Support detail (Flash): cited sentences only / sentences in the method's own words (<80% of 8-grams found in its passages):

- Plain RAG: 13.7% / 22.1%; copied sentences 1.1%; Flash-judged questions 500
- VeritasMed: 11.4% / 16.6%; copied sentences 18.2%; Flash-judged questions 500
- Strict-prompt RAG: 6.5% / 9.0%; copied sentences 3.4%; Flash-judged questions 500
