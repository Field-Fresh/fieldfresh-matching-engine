# Installation

1) make sure you have gurobi, see below for gurobi install
2) make a new virtual environment (if you want) and activate it
3) run `pip install .`

# Usage

- To run MATE (the matching engine service), run: `tomodachi run service/app.py`
- To create a matching engine testcase see `tests/`
- To run an end-to-end test, make sure the API is up and run: `tomodachi run service/app_tester.py`

# Gurobi Installation

1) Create an account or login to your account and download here: https://www.gurobi.com/downloads/gurobi-software/
2) check that you have the `grbgetkey` command in your terminal
3) Get a free academic license key here: https://www.gurobi.com/downloads/free-academic-license/
4) run the `grbgetkey ...` command with your license key, note where you save the downloaded license file
5) set the environment variable `GRB_LICENSE_FILE=/path/to/gurobi.lic`
6) run `pip install -i https://pypi.gurobi.com gurobipy`
