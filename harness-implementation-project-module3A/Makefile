.PHONY: test doctor skills check zip

test:
	python3 -m unittest discover -s harness/tests

doctor:
	python3 harness/cli/harnessctl.py doctor

skills:
	python3 harness/cli/harnessctl.py check --gate skills --strict

check: test doctor skills

zip:
	python3 scripts/package.py
