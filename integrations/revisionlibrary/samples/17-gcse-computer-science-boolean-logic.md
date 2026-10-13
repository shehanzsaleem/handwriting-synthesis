---
id: 17-gcse-computer-science-boolean-logic
title: GCSE Computer Science - Boolean expression, logic circuit and truth table
subject: GCSE Computer Science
source: Revision Library mock bank computer-science, question bool-019
marks: 6
paper: plain
hand: student-neat
pen: ballpoint
marker: teacher-red
score: 6/6
question: |
  A door alarm should sound (S) when a door sensor is triggered (D) and the alarm is armed (A), unless a valid keypad code
  has just been entered (K). Write a Boolean expression for S using D, A and K, complete a truth table for all eight
  combinations, and state whether the alarm sounds when D = 1, A = 1, K = 1.
---
## Q5

$$ S = (D \text{ AND } A) \text{ AND } (\text{NOT } K) $$ {M1 M1}

::: sketch {width: 110, height: 34}
items:
  - label: {at: [2, 8], text: "$D$"}
  - label: {at: [2, 18], text: "$A$"}
  - label: {at: [2, 29], text: "$K$"}
  - line: {points: [[7, 7], [24, 7]]}
  - line: {points: [[7, 17], [24, 17]]}
  - path: {points: [[24, 3], [32, 3], [38, 6], [40, 12], [38, 18], [32, 21], [24, 21], [24, 3]]}
  - line: {points: [[7, 28], [26, 28]]}
  - polygon: {points: [[26, 24], [26, 32], [33, 28]]}
  - circle: {at: [34.6, 28], r: 1.3}
  - line: {points: [[40, 12], [58, 12], [58, 10], [66, 10]]}
  - line: {points: [[36, 28], [58, 28], [58, 20], [66, 20]]}
  - path: {points: [[66, 6], [74, 6], [80, 9], [82, 15], [80, 21], [74, 24], [66, 24], [66, 6]]}
  - line: {points: [[82, 15], [96, 15]]}
  - label: {at: [98, 17], text: "$S$"}
:::

::: table {marks: [B1 B1], col_widths: [12, 12, 12, 30, 22, 12]}
| $D$ | $A$ | $K$ | $D$ AND $A$ | NOT $K$ | $S$ |
| $0$ | $0$ | $0$ | $0$ | $1$ | $0$ |
| $0$ | $0$ | $1$ | $0$ | $0$ | $0$ |
| $0$ | $1$ | $0$ | $0$ | $1$ | $0$ |
| $0$ | $1$ | $1$ | $0$ | $0$ | $0$ |
| $1$ | $0$ | $0$ | $0$ | $1$ | $0$ |
| $1$ | $0$ | $1$ | $0$ | $0$ | $0$ |
| $1$ | $1$ | $0$ | $1$ | $1$ | $1$ |
| $1$ | $1$ | $1$ | $1$ | $0$ | $0$ |
:::

When $D = 1$, $A = 1$, $K = 1$: $(1 \text{ AND } 1) = 1$ and NOT $1 = 0$, so $1$ AND $0 = 0$. The alarm does not sound. {M1 A1}
