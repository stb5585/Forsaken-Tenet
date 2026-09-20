# Development Tools

## dev_tools.py

Command-line interface for testing and developing game systems.

### Usage

```bash
# From project root
./.venv/bin/python tools/dev_tools.py [command] [options]
```

### Commands

#### Test Effect System
```bash
./.venv/bin/python tools/dev_tools.py effects
```
Shows all available effect types and demonstrates composite effects.

#### Test Action Queue
```bash
./.venv/bin/python tools/dev_tools.py queue
```
Demonstrates priority-based turn ordering and action scheduling.

#### Test Event System
```bash
./.venv/bin/python tools/dev_tools.py events [--verbose]
```
Shows event emission and subscription. Use `--verbose` for detailed logging.

#### Test Ability Loader
```bash
# Load all abilities from directory
./.venv/bin/python tools/dev_tools.py abilities --directory src/core/data/abilities

# Load specific ability file
./.venv/bin/python tools/dev_tools.py abilities --file src/core/data/abilities/fireball.yaml
```
Tests YAML ability loading and displays parsed ability data.

#### Generate Sample Abilities
```bash
./.venv/bin/python tools/dev_tools.py generate --output /tmp/sample_abilities
```
Creates example ability YAML files for reference. Use a scratch directory unless
you intentionally want to add new checked-in ability data.

#### Balance Simulations
```bash
./.venv/bin/python tools/dev_tools.py balance --iterations 1000
```
Runs combat simulations for balance testing (requires Character instances).

For the representative class, race, gear, progression, and enemy matrices used
by the design-gate documents, use the standalone suite:

```bash
./.venv/bin/python tools/run_balance_suite.py --help
```

#### Export Game Spreadsheets

Regenerate the reviewable CSV snapshots under `docs/spreadsheets/` after
changing classes, races, abilities, items, enemies, or quests:

```bash
./.venv/bin/python tools/export_game_spreadsheets.py
```

### Help
```bash
./.venv/bin/python tools/dev_tools.py --help
./.venv/bin/python tools/dev_tools.py [command] --help
```

## Running from Different Directories

Both tools expect to be run from the project root directory. If you need to run from elsewhere:

```bash
cd /path/to/the-forsaken-tenet
./.venv/bin/python tools/dev_tools.py [command]
```

Or adjust Python path:
```python
import sys
sys.path.insert(0, '/path/to/the-forsaken-tenet')
```
