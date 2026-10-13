---
id: 07-further-maths-matrix-inverse
title: A-level Further Maths - inverse of a 3 x 3 matrix
subject: A-level Further Maths
source: Revision Library mock bank a-level-further-maths, question mat-020
marks: 6
paper: squared
hand: student
pen: ballpoint
marker: teacher-red
score: 6/6
question: |
  Find the inverse of the matrix A = [[1, 2, 1], [0, 1, -1], [2, 3, 4]].
---
## Q3

$$ A = \begin{pmatrix} 1 & 2 & 1 \\ 0 & 1 & -1 \\ 2 & 3 & 4 \end{pmatrix} $$

$$ \det A = 1(4 + 3) - 2(0 + 2) + 1(0 - 2) \\ = 7 - 4 - 2 = 1 $$ {M1 A1}

$$ \text{cofactors} = \begin{pmatrix} 7 & -2 & -2 \\ -5 & 2 & 1 \\ -3 & 1 & 1 \end{pmatrix} $$ {M1 A1}

Transpose to get the adjugate, then divide by $\det A = 1$: {M1}

$$ A^{-1} = \begin{pmatrix} 7 & -5 & -3 \\ -2 & 2 & 1 \\ -2 & 1 & 1 \end{pmatrix} $$ {A1}

> Check row 1 of $A$ times column 1: $7 - 4 - 2 = 1$ ✓
