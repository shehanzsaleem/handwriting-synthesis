---
id: 01-alevel-maths-implicit-differentiation
title: A-level Maths - implicit differentiation and tangent
subject: A-level Maths
source: Revision Library mock bank a-level-maths, question dif-019
marks: 6
paper: lined
hand: student
pen: ballpoint
marker: teacher-red
score: 6/6
question: |
  A curve is defined implicitly by xy² − x² = 8. The point (1, 3) lies on the curve.
  Find dy/dx at this point, and hence find the equation of the tangent to the curve at (1, 3),
  giving your answer in the form y = mx + c.
---
## Q7

Differentiate each term with respect to $x$, using the product rule on $xy^2$:

$$ \frac{d}{dx}\left(xy^2\right) = y^2 + 2xy\frac{dy}{dx} $$ {M1}

$$ \frac{d}{dx}\left(x^2\right) = 2x \qquad \frac{d}{dx}(8) = 0 $$ {M1}

So the derivative of the whole equation is

$$ y^2 + 2xy\frac{dy}{dx} - 2x = 0 $$ {A1}

Substitute $x = 1$ and $y = 3$:

$$ 9 + 2(1)(3)\frac{dy}{dx} - 2 = 0 \\ 6\frac{dy}{dx} = -7 $$ {M1}

$$ \frac{dy}{dx} = -\frac{7}{6} $$ {A1}

Tangent through the point $(1, 3)$ with gradient $-\frac{7}{6}$:

$$ y - 3 &= -\frac{7}{6}(x - 1) \\ y &= -\frac{7}{6}x + \frac{7}{6} + 3 $$

$$ \boxed{y = -\frac{7}{6}x + \frac{25}{6}} $$ {A1}
