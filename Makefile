# Thin entry points for repo scripts. The logic lives in the scripts; see each one's header.

.PHONY: clean-run

# Reset the dev container to a known-good dry-run state (#21).
# Pass flags / fixture slugs through ARGS, e.g. make clean-run ARGS="--rebuild roman-numeral".
clean-run:
	./clean-run.sh $(ARGS)
