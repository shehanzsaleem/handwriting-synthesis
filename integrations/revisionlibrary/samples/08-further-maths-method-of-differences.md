---
id: 08-further-maths-method-of-differences
title: A-level Further Maths - method of differences
subject: A-level Further Maths
source: Revision Library mock bank a-level-further-maths, question sas-020
marks: 6
paper: plain
hand: student
pen: ballpoint-black
marker: teacher-red
score: 6/6
question: |
  Given that 1/(r(r+1)(r+2)) = ½[1/(r(r+1)) - 1/((r+1)(r+2))], use the method of differences to find the sum of
  1/(r(r+1)(r+2)) for r = 1 to n, in terms of n. Hence state the value of the sum to infinity.
---
## Q6

Check the identity:

$$ \frac{1}{r(r+1)} - \frac{1}{(r+1)(r+2)} = \frac{(r+2) - r}{r(r+1)(r+2)} = \frac{2}{r(r+1)(r+2)} $$ {M1}

$$ \sum_{r=1}^{n} \frac{1}{r(r+1)(r+2)} = \frac{1}{2}\left[\left(\frac{1}{1 \cdot 2} - \frac{1}{2 \cdot 3}\right) + \left(\frac{1}{2 \cdot 3} - \frac{1}{3 \cdot 4}\right) + \cdots \right] $$ {M1}

Everything cancels except the first and last terms: {M1}

$$ = \frac{1}{2}\left[\frac{1}{2} - \frac{1}{(n+1)(n+2)}\right] = \frac{1}{4} - \frac{1}{2(n+1)(n+2)} $$ {A1}

As $n \to \infty$, $\frac{1}{2(n+1)(n+2)} \to 0$, so {M1}

$$ \sum_{r=1}^{\infty} \frac{1}{r(r+1)(r+2)} = \boxed{\frac{1}{4}} $$ {A1}
