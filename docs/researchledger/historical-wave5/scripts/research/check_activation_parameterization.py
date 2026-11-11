#!/usr/bin/env python3
"""Deterministic sanity check, NOT a neural-architecture or LLM benchmark.

For f= sigmoid(2*(w*x+b)), v=2*w and c=2*b. In plain gradient descent the
(v,c) learning rate must be four times the (w,b) rate to match updates.
"""
import json
import math


def sigmoid(x):
    return 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))


def run():
    xs = [-2 + i / 8 for i in range(33)]
    ys = [float(x > 0.3) for x in xs]
    w, b = 0.15, -0.1
    v, c = 2 * w, 2 * b
    u, d = v, c
    rate = 0.02
    errors = []
    for _ in range(200):
        pa = [sigmoid(2 * (w * x + b)) for x in xs]
        pb = [sigmoid(v * x + c) for x in xs]
        pc = [sigmoid(u * x + d) for x in xs]
        errors.append(max(abs(a - z) for a, z in zip(pa, pb)))
        ga = sum((a - y) * x for a, y, x in zip(pa, ys, xs)) / len(xs)
        gb = sum(a - y for a, y in zip(pa, ys)) / len(xs)
        gv = sum((a - y) * x for a, y, x in zip(pb, ys, xs)) / len(xs)
        gc = sum(a - y for a, y in zip(pb, ys)) / len(xs)
        gu = sum((a - y) * x for a, y, x in zip(pc, ys, xs)) / len(xs)
        gd = sum(a - y for a, y in zip(pc, ys)) / len(xs)
        w -= rate * 2 * ga
        b -= rate * 2 * gb
        v -= 4 * rate * gv
        c -= 4 * rate * gc
        u -= rate * gu
        d -= rate * gd
    errors.append(max(abs(sigmoid(2 * (w * x + b)) - sigmoid(v * x + c)) for x in xs))
    control = max(abs(sigmoid(v * x + c) - sigmoid(u * x + d)) for x in xs)
    return {
        "experiment_id": "EG-V3-PRIMITIVE-02",
        "steps": 200,
        "samples": 33,
        "optimizer": "full-batch plain gradient descent; analytic BCE gradients",
        "mapped_learning_rates": [rate, 4 * rate],
        "maximum_mapped_prediction_difference": max(errors),
        "same_rate_control_final_prediction_difference": control,
        "passed": max(errors) < 1e-12 and control > 1e-3,
        "conclusion": "Function equivalence alone does not make an equal-learning-rate optimizer comparison fair.",
        "limits": "One scalar binary classification toy. No superiority, generalization or agent-performance claim.",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
