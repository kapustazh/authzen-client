## Summary

-

## Test plan

CI runs Ruff, ty, pytest on Python 3.12–3.14, and `uv build`. A pull request
fails when it changes more than 200 lines, not counting `uv.lock`.

- [ ] Local checks passed
