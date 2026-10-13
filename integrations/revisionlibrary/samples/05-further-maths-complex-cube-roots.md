---
id: 05-further-maths-complex-cube-roots
title: A-level Further Maths - cube roots of a complex number (iPad)
subject: A-level Further Maths
source: Revision Library mock bank a-level-further-maths, question cdm-009
marks: 6
paper: ipad-dots
hand: ipad
pen: ipad-blue
marker: ipad-red
score: 6/6
footer: Revision Library · worked answer · written on iPad
question: |
  Find the three cube roots of -2 + 2√3 i, giving each in the form r(cos θ + i sin θ) with θ in radians in
  the range -π < θ ≤ π. Hence find the root with the smallest positive argument in the form a + bi,
  giving a and b to 3 significant figures.
---
## Q2

$$ |w| = \sqrt{(-2)^2 + (2\sqrt{3})^2} = \sqrt{16} = 4 $$ {M1}

$$ \arg w = \pi - \arctan\sqrt{3} = \pi - \frac{\pi}{3} = \frac{2\pi}{3} $$ {M1}

$$ z = 4^{\frac{1}{3}}\left(\cos\frac{\frac{2\pi}{3} + 2k\pi}{3} + i\sin\frac{\frac{2\pi}{3} + 2k\pi}{3}\right), \quad k = 0, 1, 2 $$ {M1}

$$ \theta = \frac{2\pi}{9}, \quad \frac{8\pi}{9}, \quad \frac{14\pi}{9} - 2\pi = -\frac{4\pi}{9} $$ {A1}

::: sketch {width: 64, height: 58}
items:
  - axes: {x: [-2.2, 2.2], y: [-2, 2], box: [6, 6, 58.8, 54], xlabel: "Re", ylabel: "Im", origin_label: false}
  - circle: {at: [0, 0], r: 19.0, pen: marker}
  - point: {at: [1.216, 1.020], label: "$z_1$", offset: [1.2, -1.4]}
  - point: {at: [-1.492, 0.543], label: "$z_2$", offset: [-5.0, -1.4]}
  - point: {at: [0.276, -1.563], label: "$z_3$", offset: [1.4, 2.6]}
:::

Smallest positive argument is $\frac{2\pi}{9}$: {A1}

$$ z_1 = 4^{\frac{1}{3}}\left(\cos\frac{2\pi}{9} + i\sin\frac{2\pi}{9}\right) \approx \boxed{1.22 + 1.02i} $$ {A1}
