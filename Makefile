install:
\tpip install -r requirements.txt && pip install pytest ruff black pre-commit && pre-commit install

lint:
\truff check . && black --check .

fmt:
\tblack . && ruff check --fix .

test:
\tpytest -q || true

run:
\tpython app.py
