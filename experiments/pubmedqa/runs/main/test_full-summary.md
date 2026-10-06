| Method | Accuracy | Macro-F1 | Unsupported sentences (Flash judge) | Uncited | Retrieval hit | $ / question | Median s | Unsupported (MiniCheck, rejected) |
|---|---|---|---|---|---|---|---|---|
| Closed-book | 52.2% | 0.431 | — | 100.0% | — | $0.0014 | 7 | — |
| Plain RAG | 63.8% | 0.580 | 21.8% | 9.4% | 98.2% | $0.0012 | 10 | 44.5% |
| VeritasMed | 63.6% | 0.565 | 14.5% | 3.5% | 98.4% | $0.0105 | 59 | 21.5% |
| VeritasMed (verbatim) | 67.6% | 0.586 | 3.4% | 2.9% | 98.8% | $0.0100 | 59 | 7.4% |
| Gold abstract | 65.6% | 0.601 | 19.6% | 8.5% | — | $0.0009 | 7 | 38.9% |

Paired differences vs Plain RAG (percentage points, 95% bootstrap interval):

- A0-A1: accuracy: -11.6 [-16.8, -6.4]
- A2-A1: accuracy: -0.2 [-4.0, +3.6]; unsupported_flash: -7.3 [-9.6, -4.9]; unsupported_minicheck: -23.0 [-25.9, -20.2]
- A3-A1: accuracy: +3.8 [+0.2, +7.4]; unsupported_flash: -18.5 [-20.6, -16.4]; unsupported_minicheck: -37.1 [-39.7, -34.4]
- A4-A1: accuracy: +1.8 [-1.4, +5.2]; unsupported_flash: -1.9 [-4.6, +0.6]; unsupported_minicheck: -5.6 [-8.7, -2.6]

Support detail (Flash): cited sentences only / sentences in the method's own words (<80% of 8-grams found in its passages):

- Plain RAG: 13.7% / 22.1%; copied sentences 1.1%; Flash-judged questions 500
- VeritasMed: 11.4% / 16.6%; copied sentences 18.2%; Flash-judged questions 500
- VeritasMed (verbatim): 0.5% / 3.9%; copied sentences 59.8%; Flash-judged questions 500
- Gold abstract: 12.1% / 19.7%; copied sentences 1.0%; Flash-judged questions 491
