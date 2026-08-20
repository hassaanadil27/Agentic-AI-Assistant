# Reflection: A Failure Encountered While Building This System

> This is a template based on a realistic failure mode of this exact
> codebase. Replace the specifics below with what you actually hit while
> testing on your machine — the assignment requires an honest account of
> a real failure, not a fabricated one.

## Failure Encountered

While testing `find_cost_outliers()`, the very first run produced an
outlier list dominated by a single category ("Other") because a few
categories in the dataset have very small group sizes (some categories
have fewer than 5 projects). Computing IQR on a tiny sample gives
meaningless quartiles — a category with 2 projects will have Q1 == Q3 for
all practical purposes, and even a modest cost difference gets flagged as
"infinitely" outlying.

## Why It Happened

The initial implementation of `find_cost_outliers()` ran the IQR
calculation on every category group regardless of size, trusting that
`pandas.Series.quantile()` would silently do "something reasonable" even
for very small groups. It technically didn't crash — it just produced
statistically meaningless flags, which is arguably worse, because the
Finance Agent would have reported them with full confidence.

## How It Was Diagnosed

Running `tests/test_tools.py::test_cost_outliers_are_actually_above_fence`
against the real dataset and manually inspecting the returned
`OutlierResult` objects for the smallest categories (`Social Welfare`, 12
rows; `Sewerage`, 24 rows) showed several "outliers" whose cost was only
marginally above the fence, with Q1/Q3 nearly identical — a strong signal
that the underlying sample size was too small for the method to be
defensible.

## Fix

Added a `min_group_size` parameter (default 5) to `find_cost_outliers()`
in `tools/finance_tools.py`. Categories with fewer rows than this
threshold are skipped entirely rather than flagged — the system now
reports "no statistically defensible outlier check possible" implicitly
by omission, instead of inventing a confident-sounding but meaningless
result. This is documented directly in the function's docstring so it's
easy to explain in a viva.

## What I Learned

A tool that "doesn't crash" is not the same as a tool that "doesn't
mislead." Anti-hallucination isn't only about the LLM — it's just as
important to make sure the *deterministic* Python tools underneath the
agent don't quietly manufacture false confidence from insufficient data.
The fix cost five lines of code but meaningfully changed what the Finance
Agent is allowed to claim.
