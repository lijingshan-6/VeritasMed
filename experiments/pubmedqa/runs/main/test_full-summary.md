| Method | Accuracy | Macro-F1 | Unsupported sentences | Consistent with paper | Retrieval hit | $ / question | Median s |
|---|---|---|---|---|---|---|---|
| Closed-book | 52.2% | 0.431 | — | 17.9% | — | $0.0014 | 7 |
| Plain RAG | 63.8% | 0.580 | 44.5% | 56.7% | 98.2% | $0.0012 | 10 |
| VeritasMed | 63.6% | 0.565 | 21.5% | 77.6% | 98.4% | $0.0105 | 59 |
| Gold abstract | 65.6% | 0.601 | 38.9% | 65.4% | — | $0.0009 | 7 |

Paired differences vs Plain RAG (percentage points, 95% bootstrap interval):

- A0-A1: accuracy: -11.6 [-16.8, -6.4]; paper_consistency: -38.8 [-42.1, -35.6]
- A2-A1: accuracy: -0.2 [-4.0, +3.6]; paper_consistency: +20.9 [+17.9, +23.8]; unsupported_rate: -23.0 [-25.9, -20.2]
- A4-A1: accuracy: +1.8 [-1.4, +5.2]; paper_consistency: +8.7 [+5.9, +11.5]; unsupported_rate: -5.6 [-8.7, -2.6]
