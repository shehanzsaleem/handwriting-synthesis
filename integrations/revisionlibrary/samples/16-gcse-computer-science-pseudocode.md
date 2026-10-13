---
id: 16-gcse-computer-science-pseudocode
title: GCSE Computer Science - designing an algorithm in pseudocode
subject: GCSE Computer Science
source: Revision Library mock bank computer-science, question alg-019
marks: 6
paper: squared
hand: student-quick
pen: ballpoint-black
marker: teacher-red
score: 6/6
question: |
  Design an algorithm, in pseudocode, that takes a list of 10 exam scores and outputs how many scores fall into each
  of three bands: below 40, from 40 to 69 inclusive, and 70 or above.
---
## Q7

::: code {marks: [B1 B1 B1 B1 B1 B1]}
below = 0
mid = 0
high = 0
for i = 0 to 9
    if scores[i] < 40 then
        below = below + 1
    elseif scores[i] <= 69 then
        mid = mid + 1
    else
        high = high + 1
    endif
next i
print(below)
print(mid)
print(high)
:::

> Three counters set to 0, a loop over all 10 scores, three selections, outputs after the loop.
