---
id: 19-alevel-economics-supply-shift
title: A-level Economics - supply shift and producer surplus (iPad)
subject: A-level Economics
source: Revision Library mock bank a-level-economics, question dsp-019
marks: 6
paper: ipad-grid
hand: ipad
pen: pencil-ipad
marker: ipad-red
score: 6/6
footer: Revision Library · worked answer · written on iPad
question: |
  A breakthrough cuts the production cost of solar panels. Demand is Qd = 500 - 10P (P in pounds per panel, Q in
  thousands per year). Before the breakthrough supply was Qs = 50 + 15P; after it, Qs = 200 + 15P. Calculate the original
  and new equilibrium price and quantity, and analyse the effect on producer surplus, referring to existing and new
  producers.
---
## Q4

Original: $500 - 10P = 50 + 15P \Rightarrow 25P = 450$ {M1}

$$ P = 18, \quad Q = 500 - 180 = 320 $$ {A1}

New: $500 - 10P = 200 + 15P \Rightarrow 25P = 300$ {M1}

$$ P = 12, \quad Q = 500 - 120 = 380 $$ {A1}

::: sketch {width: 96, height: 58}
items:
  - axes: {x: [0, 520], y: [0, 50], box: [12, 6, 90, 50], xlabel: "Q", ylabel: "P", xticks: [320, 380], yticks: [12, 18], origin_label: false, arrows: true}
  - plot: {f: "(500 - x)/10", x: [40, 500], label: "D"}
  - plot: {f: "(x - 50)/15", x: [50, 470], label: "$S_1$"}
  - plot: {f: "(x - 200)/15", x: [200, 500], label: "$S_2$", pen: marker}
  - dashed: {points: [[320, 0], [320, 18], [0, 18]]}
  - dashed: {points: [[380, 0], [380, 12], [0, 12]]}
:::

Producer surplus is affected two ways: a lower price received on every panel, but a higher quantity sold. {B1}

Existing producers lose some surplus from the price falling from 18 to 12, but their costs have also fallen, and new lower-cost producers can now enter, so total producer surplus is likely to rise overall. {B1}
