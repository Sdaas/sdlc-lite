# Acceptance container image — a STRANGER'S MACHINE, not the dev container (#100).
#
# Built and run only by ../acceptance.sh. Purpose and rules: dev-docs/ACCEPTANCE.md.
#
# What a stranger has:  Python 3.12, git, curl, the latest Claude Code, a git identity,
#                       and their own small Python repo (~/mypackage).
# What they do NOT have: the sdlc-lite plugin, the dev toolchain (ruff, mypy, pytest,
#                       mutmut ...), a venv, a Claude login, or anything from this repo.
# Keep it that way: every extra here hides a step the README must describe.
FROM python:3.12-slim

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# A non-root user, like a person on their own laptop.
RUN useradd --create-home --shell /bin/bash stranger
USER stranger
WORKDIR /home/stranger
ENV PATH="/home/stranger/.local/bin:${PATH}"

# Latest Claude Code from the official installer — what a stranger gets today. Not pinned,
# and the auto-updater stays on. acceptance.sh builds with --no-cache so "latest" is fresh.
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

RUN git config --global user.name "Stranger" \
    && git config --global user.email "stranger@example.invalid" \
    && git config --global init.defaultBranch main

# The stranger's own repo. Prove its 2 tests pass with a throwaway venv, then remove every
# trace of that check before the first commit — the repo starts with no venv and no tools.
COPY --chown=stranger:stranger mypackage/ /home/stranger/mypackage/
RUN cd mypackage \
    && python -m venv /tmp/seedcheck \
    && /tmp/seedcheck/bin/pip install --quiet --disable-pip-version-check pytest \
    && PYTHONPATH=src /tmp/seedcheck/bin/python -m pytest -q -p no:cacheprovider tests \
    && rm -rf /tmp/seedcheck \
    && find . -name __pycache__ -type d -prune -exec rm -rf {} + \
    && git init -q \
    && git add -A \
    && git commit -q -m "Initial commit"

COPY --chown=stranger:stranger bashrc-acceptance /home/stranger/.bashrc-acceptance
RUN echo '. ~/.bashrc-acceptance' >> /home/stranger/.bashrc

WORKDIR /home/stranger/mypackage
CMD ["sleep", "infinity"]
