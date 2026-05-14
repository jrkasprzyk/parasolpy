# Installation

## From PyPI

```bash
pip install parasolpy
```

`parasolpy` requires Python 3.12 or newer.

## From Source

Development installs use Poetry:

```bash
git clone https://github.com/jrkasprzyk/parasolpy.git
cd parasolpy
poetry install
```

Run the test suite with:

```bash
poetry run pytest -q
```

## Documentation Dependencies

To build these docs locally, install the optional docs dependencies:

```bash
pip install ".[docs]"
sphinx-build -W -b html docs docs/_build/html
```

With Poetry, install the project first and run Sphinx inside the Poetry environment:

```bash
poetry install
poetry run sphinx-build -W -b html docs docs/_build/html
```
