---
id: 04-alevel-maths-point-of-inflection
title: A-level Maths - point of inflection with a sketch
subject: A-level Maths
source: Revision Library mock bank a-level-maths, question dif-015
marks: 6
paper: lined
hand: teacher
pen: gel
marker: teacher-red
question: |
  A curve has equation y = x³ - 6x² + 9x + 2. Find the coordinates of the point of inflection on the curve,
  justifying that it is a point of inflection.
---
## Q6 (model answer)

$$ \frac{dy}{dx} = 3x^2 - 12x + 9 $$ {M1}

$$ \frac{d^2y}{dx^2} = 6x - 12 $$ {M1}

Set $\frac{d^2y}{dx^2} = 0$: $6x - 12 = 0$, so $x = 2$ {M1}

Check the sign either side: at $x = 1.9$, $\frac{d^2y}{dx^2} = -0.6 < 0$; at $x = 2.1$, $\frac{d^2y}{dx^2} = 0.6 > 0$. The sign changes, so the curvature changes. {A1}

$$ y = 2^3 - 6(2)^2 + 9(2) + 2 = 8 - 24 + 18 + 2 = 4 $$ {A1}

$$ \boxed{\text{point of inflection } (2, 4)} $$ {A1}

::: sketch {width: 92, height: 56}
items:
  - axes: {x: [-0.5, 4.5], y: [-1, 8], box: [8, 6, 88, 52], xlabel: "$x$", ylabel: "$y$", xticks: [1, 2, 3], yticks: [2, 4, 6]}
  - plot: {f: "x**3 - 6*x**2 + 9*x + 2", x: [-0.25, 4.15], clip: [-1, 8]}
  - point: {at: [1, 6], label: "max $(1, 6)$", offset: [1.2, -2.0]}
  - point: {at: [3, 2], label: "min $(3, 2)$", offset: [1.4, 3.2]}
  - point: {at: [2, 4], label: "inflection $(2, 4)$", pen: marker, offset: [1.6, -0.8]}
:::
