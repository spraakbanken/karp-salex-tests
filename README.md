# Test scripts for Salex in Karp

This repository contains scripts for testing Salex.

To install:

1. Make sure you have `karp-backend` installed.
2. Run `poetry shell` **inside of `karp-backend`**.
3. Then run `poetry install` in this directory, to install all dependencies.

To run the tests, run `karp-cli repl run_tests.py`. The test results
will be stored in the `results` subdirectory in HTML and XLSX formats.

The directory structure is as follows:

* `tests/`: individual test scripts, run by `run_tests.py`.
* `utils/`: various helper functions and classes for getting
  data from Salex, plus libraries for writing tests and generating
  formatted test output
* `templates/`: HTML templates for the test report
* `old`/: old test scripts that haven't yet been converted to work
  with `run_tests.py`

Tests for the Salex export process are not yet included in this repository.
