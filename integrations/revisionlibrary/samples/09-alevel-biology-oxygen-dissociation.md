---
id: 09-alevel-biology-oxygen-dissociation
title: A-level Biology - oxygen dissociation curves
subject: A-level Biology
source: Revision Library mock bank a-level-biology, question exg-010
marks: 6
paper: lined
hand: student-neat
pen: ballpoint
marker: teacher-red
score: 6/6
question: |
  A student compares the oxygen dissociation curves of adult human haemoglobin, llama haemoglobin
  (high altitude, low oxygen partial pressure) and fetal human haemoglobin. At pO2 = 4 kPa: adult 40%,
  llama 65%, fetal 55% saturated. Calculate the difference in percentage saturation between llama and adult
  haemoglobin at 4 kPa, and explain, in terms of the position of the curve, why llama and fetal haemoglobin
  both have a higher affinity for oxygen than adult haemoglobin.
---
## Q3

Difference at 4 kPa: $65 - 40 = 25$ percentage points {M1 A1}

::: sketch {width: 112, height: 68}
items:
  - axes: {x: [0, 12], y: [0, 100], box: [14, 4, 106, 56], xlabel: "pO2 / kPa", ylabel: "% saturation", xticks: [4, 8, 12], yticks: [50, 100], origin_label: false}
  - plot: {f: "100*x**2.6/(x**2.6 + 4.8**2.6)", x: [0.2, 12], label: "adult"}
  - plot: {f: "100*x**2.6/(x**2.6 + 3.3**2.6)", x: [0.2, 11.5], label: "llama", label_at: [9.6, 97]}
  - dashed: {points: [[4, 0], [4, 65]]}
  - dashed: {points: [[0, 65], [4, 65]]}
  - dashed: {points: [[0, 40], [4, 40]]}
  - arrow: {points: [[6.8, 60], [5.2, 76]], pen: marker}
  - label: {at: [6.9, 56], text: "curve shifted left", pen: marker, scale: 0.8}
:::

Both llama and fetal haemoglobin have dissociation curves further to the left of the adult curve. {B1}

A curve further left reaches the same percentage saturation at a lower partial pressure of oxygen, so the haemoglobin has a higher affinity for oxygen. {B1}

The llama lives at high altitude where the partial pressure of oxygen in the air is low, so it needs this higher affinity to load oxygen in the lungs. {B1}

Fetal haemoglobin must take oxygen from the mother's blood across the placenta, so its higher affinity means oxygen moves from the mother's haemoglobin to the fetus. {B1}
