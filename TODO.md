# Project Restructuring Plan

## Core Components (src/core/)
- [x] Extract Order class from order_book.py into new order.py
- [x] Extract matching logic into new matching_engine.py
- [x] Create utils.py for utility functions
- [x] Update order_book.py to import from new files

## Strategies (src/strategies/)
- [x] Move strategy.py to src/strategies/market_maker.py
- [x] Update imports in market_maker.py

## Backtesting (src/backtest/)
- [x] Move backtester.py to src/backtest/backtester.py
- [x] Move performance_metrics.py to src/backtest/analytics.py
- [x] Create execution_sim.py for simulation logic
- [x] Update imports in backtester files

## Tests (tests/)
- [x] Move all test_*.py files to tests/ directory

## Data Organization
- [x] Move CSV files to data/ directory
- [x] Move PNG images to assets/ directory
- [x] Move HTML reports to assets/ directory

## Main Entry Point
- [x] Move main.py to src/main.py
- [x] Update imports in main.py

## Update All Imports
- [x] Update import statements in all files to reflect new locations
- [x] Test that all imports work correctly

## Verification
- [ ] Run tests to ensure functionality is preserved
- [x] Update README.md with new structure
- [ ] Create sample data files if needed
