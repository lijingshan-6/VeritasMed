| Method | Accuracy | Macro-F1 | Unsupported sentences | Consistent with paper | Retrieval hit | $ / question | Median s |
|---|---|---|---|---|---|---|---|
| Closed-book | 52.0% | 0.397 | — | 16.7% | — | $0.0012 | 6 |
| Plain RAG | 62.0% | 0.566 | 48.7% | 50.0% | 98.0% | $0.0013 | 12 |
| VeritasMed | 62.0% | 0.528 | 20.0% | 77.2% | 100.0% | $0.0101 | 64 |
| Gold abstract | 72.0% | 0.651 | 37.2% | 64.1% | — | $0.0009 | 6 |

Paired differences vs Plain RAG (percentage points, 95% bootstrap interval):

- A0-A1: accuracy: -10.0 [-28.0, +8.0]; paper_consistency: -33.3 [-43.6, -22.9]
- A2-A1: accuracy: +0.0 [-14.0, +14.0]; paper_consistency: +27.2 [+18.8, +35.6]; unsupported_rate: -28.7 [-37.8, -19.6]
- A4-A1: accuracy: +10.0 [+0.0, +20.0]; paper_consistency: +14.1 [+4.5, +23.8]; unsupported_rate: -11.6 [-20.3, -2.8]
