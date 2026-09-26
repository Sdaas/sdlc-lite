# Base image: Microsoft's Debian-based devcontainer image with Python 3.12
# preinstalled. It already includes git, curl, common build tools, and a
# non-root "vscode" user set up for development. Python is what the real
# /implement-feature product generates and tests.
FROM mcr.microsoft.com/devcontainers/python:3.12

# A few shell niceties (git/curl are already in the base image). tmux hosts the
# hands-off T3 session the human attaches to (#66, dev-docs/t3-runs.md).
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        bash-completion \
        jq \
        tmux \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager) into the non-root user's environment.
# The official installer places it in ~/.local/bin. We'll use it for the real
# product's venv + test deps (pytest, mutation testing) later.
USER vscode
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/vscode/.local/bin:${PATH}"

# Default working directory. VS Code / the devcontainer CLI mount the repo under
# /workspaces/<repo>; setting this keeps sessions sensible.
WORKDIR /workspaces

# Claude Code CLI, PINNED to an exact version (#59). The official devcontainer
# feature has no version option — it installs whatever npm has at build time — so
# the version lived only in the image cache. The native installer takes an exact
# version and needs no Node. Bump = edit CLAUDE_VERSION + rebuild. Auto-update
# stays off (DISABLE_AUTOUPDATER in devcontainer.json) so the pin holds.
# Installs to ~/.local/bin (already on PATH above), outside the ~/.claude volume.
ARG CLAUDE_VERSION=2.1.281
RUN curl -fsSL https://claude.ai/install.sh | bash -s "${CLAUDE_VERSION}" \
    && claude --version
