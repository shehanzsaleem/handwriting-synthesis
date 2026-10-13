---
id: 03-alevel-maths-trapezium-rule
title: A-level Maths - trapezium rule (iPad)
subject: A-level Maths
source: Revision Library mock bank a-level-maths, question int-010
marks: 6
paper: ipad-grid
hand: ipad
pen: pencil-ipad
marker: ipad-red
score: 6/6
footer: Revision Library · worked answer · written on iPad
question: |
  Use the trapezium rule with 4 strips to estimate the value of the integral of √(1 + x³) with respect to x
  between x = 0 and x = 2, giving your answer to 3 significant figures. Use a table of values at
  x = 0, 0.5, 1, 1.5, 2.
---
## Q9

$y = \sqrt{1 + x^3}$, strip width $h = \frac{2 - 0}{4} = 0.5$ {M1}

::: table {marks: [M1]}
| $x$ | $0$ | $0.5$ | $1$ | $1.5$ | $2$ |
| $y$ | $1$ | $1.0607$ | $1.4142$ | $2.0917$ | $3$ |
:::

$$ \int_0^2 \sqrt{1 + x^3}\,dx \approx \frac{h}{2}\left[y_0 + y_4 + 2(y_1 + y_2 + y_3)\right] $$ {M1}

$$ = 0.25\left[1 + 3 + 2(1.0607 + 1.4142 + 2.0917)\right] \\ = 0.25\left[4 + 2(4.5666)\right] $$ {A1}

$$ = 0.25 \times 13.1332 = 3.2833 $$ {A1}

$$ \boxed{\approx 3.28 \text{ (3 s.f.)}} $$ {A1}
