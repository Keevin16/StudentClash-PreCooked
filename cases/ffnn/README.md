# Test case: feed-forward network from scratch (synthetic, no real student data)

- `assignment.md` — what to type in the professor's "New assignment" form
- `course/ffnn-notes.md` — course material (upload with the assignment)
- `deliverable/report.pdf`, `deliverable/mlp.py` — what the fake student "Marco Bianchi" submits

## Planted flaws (answer key — do NOT upload)
1. **Initialisation mismatch:** report §2.3 claims Xavier, `mlp.py:25` sets `W1` to zeros (symmetry is only broken by the random `W2`).
2. **Test-set leakage:** learning rate (§3) and early stopping (`mlp.py:68-71`) are both chosen on the *test* set; no validation split, so the 95.0% is optimistic.
3. **Overfitting reasoning:** §4 says "train loss keeps going down, so no overfitting" — that is not evidence (needs validation loss); the 95.0 → 93.8% drop is dismissed as noise.
4. **Sigmoid in the hidden layer** justified only by "simple derivative" (§2.1); ignores saturation / vanishing gradients and the lr = 2.0 needed to compensate.
5. **"Deeper networks are always more accurate"** (§5) — false.
6. Report says "lines 36–48" for backward; it is lines 34–46 (minor anchor error).
