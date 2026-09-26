# Thin entry points for repo scripts. The logic lives in the scripts; see each one's header.

.PHONY: clean-run t3-start t3-attach t3-peek t3-watch t3-stop

# Reset the dev container to a known-good dry-run state (#21).
# Pass flags / fixture slugs through ARGS, e.g. make clean-run ARGS="--rebuild roman-numeral".
clean-run:
	./clean-run.sh $(ARGS)

# Hands-off T3 runs (#66): the session runs in tmux inside the container.
# Guide: dev-docs/t3-runs.md. E.g. make t3-start SLUG=roman-numeral, then make t3-attach.
t3-start:
	@test -n "$(SLUG)" || { echo "usage: make t3-start SLUG=<fixture slug>" >&2; exit 2; }
	./t3-run.sh start $(SLUG)

t3-attach:
	@./t3-run.sh attach

t3-peek:
	@./t3-run.sh peek

t3-watch:
	@./t3-run.sh watch

t3-stop:
	@./t3-run.sh stop
