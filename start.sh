#!/bin/bash
# AgentKit — Startup script
# The user runs: bash start.sh

set -e

echo ""
echo "==========================================================="
echo "   AgentKit — WhatsApp AI Agent Builder"
echo "==========================================================="
echo ""
echo "  Preparing your environment to build your AI agent..."
echo ""

# ── Check Python ──────────────────────────────────────────
echo "  [1/4] Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "  ERROR: Python 3 not found."
    echo "  Download it at: https://python.org/downloads"
    echo ""
    exit 1
fi

PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo ""
    echo "  ERROR: You need Python 3.11 or higher."
    echo "  Current version: $(python3 --version)"
    echo "  Download the latest version at: https://python.org/downloads"
    echo ""
    exit 1
fi
echo "  OK — $(python3 --version)"

# ── Check Claude Code ────────────────────────────────────
echo "  [2/4] Checking Claude Code..."
if ! command -v claude &> /dev/null; then
    echo ""
    echo "  Claude Code is not installed."
    echo ""
    echo "  To install it:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "  If you don't have npm/Node.js:"
    echo "    https://nodejs.org (download LTS)"
    echo ""
    echo "  After installing, run 'claude' once to authenticate"
    echo "  and then run again: bash start.sh"
    echo ""
    exit 1
fi
echo "  OK — Claude Code installed"

# ── Create base folders ──────────────────────────────────
echo "  [3/4] Preparing folders..."
mkdir -p knowledge
echo "  OK — Structure ready"

# ── Done ─────────────────────────────────────────────────
echo "  [4/4] All verified"

echo ""
echo "==========================================================="
echo ""
echo "  All set. Now open Claude Code:"
echo ""
echo "    claude"
echo ""
echo "  And type:"
echo ""
echo "    /build-agent"
echo ""
echo "  Claude Code will guide you step by step to build"
echo "  your custom WhatsApp AI agent."
echo ""
echo "==========================================================="
echo ""
