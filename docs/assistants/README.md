# Assistant Logs & Docs

This directory contains all documents and action logs produced by the Arch Linux Assistant.

This is deliberately not for runtime app logs, test outputs, or developer-written notes


## What's Here

- Summarized reports on architecture, cli, dependencies, and refactoring
- Logs of missing or failed actions
- Cleanup docs or user-assisted scripts with explanations

- Any assistant using this repo should create logs here, and only here


## Structure

- `docs/assistants`
    - `logs/`       - repo level errors, overrides, task results
    - sessions/    - full session traces and command runs
    - reports/      - summary repo scans and decisions

## ChatGPT Trading Bot

To run the automated trading loop powered by ChatGPT, select
**"Run ChatGPT Trading Bot"** from the CLI or main menu. The bot
collects account data, sends it to ChatGPT for decision making and
executes the returned orders automatically.
