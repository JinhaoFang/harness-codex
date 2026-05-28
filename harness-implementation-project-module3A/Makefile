.PHONY: test doctor validate ci skills check zip

test:
	python3 -m unittest discover -s harness/tests

doctor:
	python3 harness/cli/harnessctl.py doctor

validate:
	python3 harness/cli/harnessctl.py validate --all --strict

ci:
	python3 harness/cli/harnessctl.py ci --strict

skills:
	python3 harness/cli/harnessctl.py check --gate skills --strict

check: test doctor validate ci skills

zip:
	python3 scripts/package.py
