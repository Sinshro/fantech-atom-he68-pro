# Developer guide

Use Python 3.13+.

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Never add packet bytes based on product similarity, marketing labels, or guessed
effect IDs. Add a fixture from a captured command, explain its comparison method in
`docs/PROTOCOL.md`, and test the serializer and ACK behavior first.
