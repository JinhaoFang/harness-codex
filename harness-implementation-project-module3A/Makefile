.PHONY: test doctor validate ci skills check zip release

PYTHON ?= python3

# PYTHONDONTWRITEBYTECODE keeps validation from creating package noise.
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s harness/tests -v

doctor:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) harness/cli/harnessctl.py doctor

validate:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) harness/cli/harnessctl.py validate --all --strict

ci:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) harness/cli/harnessctl.py ci --strict

skills:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) harness/cli/harnessctl.py check --gate skills --strict

check: test doctor validate ci skills

zip:
	$(PYTHON) scripts/package.py

release:
	$(PYTHON) scripts/package.py --verify
