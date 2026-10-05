Flash vs MiniCheck on 998 cited sentences (100 questions x A1, A2, A4): agreement 73.1%, Cohen's kappa 0.19

| Method | Sentences | Unsupported (MiniCheck) | Unsupported (Flash) | Agreement |
|---|---|---|---|---|
| Plain RAG | 290 | 37.6% | 12.8% | 64.1% |
| VeritasMed | 425 | 18.1% | 11.8% | 81.4% |
| Gold abstract | 283 | 32.5% | 13.1% | 70.0% |

VeritasMed - plain RAG, unsupported among cited sentences (minicheck): -18.1 pp [-23.7, -12.8] over 96 questions
VeritasMed - plain RAG, unsupported among cited sentences (flash): -0.5 pp [-4.9, +3.8] over 96 questions

Cost $0.53. Flash also generated and checked VeritasMed's answers and may favour them.
