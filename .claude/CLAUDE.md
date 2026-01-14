# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Senzing mapper that converts Dow Jones watchlist XML files to JSON format for loading into Senzing entity resolution. Supported Dow Jones feeds:

- Risk and Compliance (PFA)
- High Risk File (HRF)
- Adverse Media Entities (AME)
- Trifecta (combined PFA, AME, SOC)

## Development Setup

**External Dependency**: Requires [mapper-base](https://github.com/Senzing/mapper-base) in PYTHONPATH:

```console
export PYTHONPATH=$PYTHONPATH:/path/to/mapper-base
```

Directory structure expectation:

```console
/senzing/mappers/mapper-base
/senzing/mappers/mapper-dowjones  <-- this repo
```

## Common Commands

**Install development dependencies** (Python 3.10+):

```console
pip install --dependency-groups=all -e .
```

**Linting**:

```console
black --check src/
isort --check-only src/
flake8 src/
pylint src/
bandit -r src/
mypy src/
```

**Format code**:

```console
black src/
isort src/
```

**Run the mapper**:

```console
python src/dj_mapper.py -i <input.xml> -o <output.json> -d DJ-TRI
```

## Architecture

Single-file mapper (`src/dj_mapper.py`) with these main components:

- **XML Parsing**: Uses `xml.etree.ElementTree.iterparse()` for streaming large files in two passes:
  1. First pass: Loads reference data (country codes, relationship codes, entity associations)
  2. Second pass: Processes Person/Entity records via `g2Mapping()`

- **g2Mapping()**: Core transformation function that maps Dow Jones XML elements to Senzing JSON format including names, dates, addresses, identifiers, countries, and relationships

- **base_mapper dependency**: External library (mapper-base) provides `base_library` class for ISO code lookups, date formatting, and JSON composition

## Configuration

- `src/dj_config_updates.g2c`: Senzing configuration file defining data sources, features, and attributes needed to load Dow Jones data

## Code Style

- Line length: 120 characters
- Uses black + isort (black profile)
- Pylint config disables: `line-too-long`, `too-many-branches`, `too-many-statements`, `invalid-name`
