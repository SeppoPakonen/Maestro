.PHONY: help test truth-gate

help:
	@echo "Maestro Makefile"
	@echo "Available targets:"
	@echo "  help        - Show this help message"
	@echo "  test        - Run tests"
	@echo "  truth-gate  - Run the CI Truth Gate (docs are truth + rule-assertive contracts)"

test:
	bash tools/test/run.sh

truth-gate:
	bash scripts/truth_gate.sh
