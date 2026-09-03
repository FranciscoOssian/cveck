# ATS Scoring Engine & Anti-Stuffing

CVECK implements a **deterministic, non-probabilistic ATS evaluation engine** (`src/tools/ats_scorer.py`).

## Mathematical Scoring Formula

The overall score ($S$) is calculated as a weighted combination of **Mandatory Requirements Coverage** ($C_{req}$) and **Differential / Optional Requirements Coverage** ($C_{opt}$):

$$S = 0.70 \times C_{req} + 0.30 \times C_{opt}$$

- **Mandatory Requirements Coverage ($C_{req}$):** Percentage of `required: true` terms present in the extracted PDF text.
- **Differential Coverage ($C_{opt}$):** Percentage of `required: false` terms present in the extracted PDF text.
- **Approval Criteria:**
  - $S \ge 85.0\%$
  - $C_{req} = 100\%$ (Zero missing mandatory requirements, excluding verified gaps in `GAPS.md`).

---

## Word Boundary Matching

To prevent substring false-positives (e.g., matching `Go` inside `Google` or `C` inside `CSS`), technical keywords are evaluated with regex lookaround boundaries:

```python
def term_pattern(term: str) -> re.Pattern:
    escaped = re.escape(normalize(term))
    return re.compile(rf"(?<!\w){escaped}(?!\w)")
```

---

## Anti-Keyword Stuffing Threshold

Modern ATS parsers penalize resumes that repeat keywords artificially. CVECK calculates keyword density ($D$):

$$D = \frac{\text{Occurrences of Term}}{\text{Total Resume Words}}$$

If $D > 0.02$ (2.0% density), CVECK flags the term with a **`stuffing_flag`** and prompts `cv_refiner` to reduce redundant mentions during the next reflection loop.