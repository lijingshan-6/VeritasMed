// Two runtime modes: live Ask (full API) or read-only replay of saved conversations.
export const isReplayOnly = import.meta.env.VITE_REPLAY_ONLY === '1'

// Questions answerable from the three bundled papers.
export const demoQuestions = [
  'In the GRADE report on hypoglycemia outcomes, what were the severe hypoglycemia percentages for glargine, glimepiride, liraglutide and sitagliptin while taking the assigned medication?',
  'In the 2016 brown-rice-based vegan diet trial, what HbA1c changes were reported for the two groups?',
  'What did the 2013 aerobic versus combined exercise study measure, and over what time period?',
]
