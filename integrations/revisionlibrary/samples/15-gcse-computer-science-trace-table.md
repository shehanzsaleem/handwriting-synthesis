---
id: 15-gcse-computer-science-trace-table
title: GCSE Computer Science - trace table for finding the largest value
subject: GCSE Computer Science
source: Revision Library mock bank computer-science, question alg-017
marks: 5
paper: lined
hand: student
pen: ballpoint
marker: teacher-red
score: 5/5
question: |
  The following pseudocode is run:  numbers = [4, 9, 2, 7]  largest = numbers[0]  for i = 1 to 3  if numbers[i] > largest
  then  largest = numbers[i]  endif  next i  print largest.  Trace this pseudocode, stating the value of largest before the
  loop starts and after each comparison, and state the final value printed.
---
## Q3

Before the loop: largest $= 4$, from numbers[0] {B1}

::: table {col_widths: [16, 30, 46, 26]}
| $i$ | numbers[i] | numbers[i] > largest? | largest |
| | | | $4$ |
| $1$ | $9$ | $9 > 4$ True | $9$ |
| $2$ | $2$ | $2 > 9$ False | $9$ |
| $3$ | $7$ | $7 > 9$ False | $9$ |
:::

When $i = 1$, $9 > 4$ so largest becomes $9$ {B1}

When $i = 2$, $2$ is not greater than $9$, so largest stays $9$ {B1}

When $i = 3$, $7$ is not greater than $9$, so largest stays $9$ {B1}

Output: $9$ {A1}
