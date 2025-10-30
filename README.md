# Order Book Trading Bot

This project implements a market making trading bot with order book management, supporting both Python and C++ implementations.

## Project Structure

```
project-root/
├── python/              # All Python code
│   ├── src/             # Source code
│   ├── tests/           # Unit tests
│   └── scripts/         # Utility scripts
│   └── requirements.txt # Python dependencies
├── cpp/                 # All C++ code
│   ├── include/         # Header files
│   ├── src/             # Implementation files
│   └── tests/           # Unit tests or small executables
├── docs/                # Documentation and assets
│   ├── assets/          # Charts, reports, images
│   ├── data/            # Sample data files
│   ├── logs/            # Log files
│   ├── notebooks/       # Jupyter notebooks
│   ├── README.md        # Original README
│   └── .gitignore       # Git ignore rules
└── README.md            # This file
```

## Getting Started

### Python Implementation

1. Navigate to the python directory:
   ```bash
   cd python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the simulation:
   ```bash
   python src/main.py
   ```

### C++ Implementation

1. Navigate to the cpp directory:
   ```bash
   cd cpp
   ```

2. Compile the code (assuming you have a build system set up).

## Features

- Real-time market data integration (Alpaca API)
- Order book management
- Market making strategies
- Backtesting capabilities
- Performance visualization

## Documentation

See `docs/README.md` for detailed documentation.
