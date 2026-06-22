.PHONY: doctor validate ci skills check

PYTHON ?= python3

# Adopted repositories validate the installed harness surface and use their own
# project test/release flows separately.
doctor:
	PYTHONDONTWRITEBYTECODE=1 ./harnessctl doctor

validate:
	PYTHONDONTWRITEBYTECODE=1 ./harnessctl validate --all --strict

ci:
	PYTHONDONTWRITEBYTECODE=1 ./harnessctl ci --strict

skills:
	PYTHONDONTWRITEBYTECODE=1 ./harnessctl check --gate skills --strict

check: doctor validate ci skills
