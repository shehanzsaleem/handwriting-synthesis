---
id: 06-further-maths-proof-by-induction
title: A-level Further Maths - proof by induction
subject: A-level Further Maths
source: Revision Library mock bank a-level-further-maths, question pbi-020
marks: 6
paper: lined
hand: teacher
pen: gel
marker: teacher-red
question: |
  Prove by induction that the sum of r × r! for r = 1 to n is (n + 1)! - 1, for all positive integers n.
---
## Q4 (model answer)

Base case, $n = 1$: LHS $= 1 \times 1! = 1$, RHS $= 2! - 1 = 1$. True for $n = 1$. {B1}

Assume true for $n = k$:

$$ \sum_{r=1}^{k} r \times r! = (k + 1)! - 1 $$ {M1}

Add the $(k+1)$th term to both sides:

$$ \sum_{r=1}^{k+1} r \times r! = (k + 1)! - 1 + (k + 1)(k + 1)! $$ {M1}

$$ = (k + 1)!\left[1 + (k + 1)\right] - 1 \\ = (k + 1)!(k + 2) - 1 $$ {M1}

$$ = (k + 2)! - 1 = ((k + 1) + 1)! - 1 $$ {A1}

This is the statement for $n = k + 1$. So if it is true for $n = k$ it is true for $n = k + 1$, and it is true for $n = 1$, so by induction it is true for all positive integers $n$. {B1}
