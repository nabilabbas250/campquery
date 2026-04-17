# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`campquery` is a Python project (Python 3.14) using Streamlit as the web UI framework with Claude AI (Anthropic SDK) integration. The virtual environment is at `./venv/`.

## Environment Setup

Activate the virtual environment before running any commands:

```bash
source venv/bin/activate
```

## Running the App

Once source files exist, the Streamlit app is typically run with:

```bash
streamlit run app.py
```

## Key Dependencies

- **Streamlit** — web UI framework
- **Anthropic** — Claude API client for LLM integration
- **Pandas / NumPy / PyArrow** — data processing
- **Altair / Pydeck** — data visualization
- **Pydantic** — data validation and modeling
- **Faker** — synthetic data generation
- **GitPython** — programmatic git operations
- **Tenacity** — retry logic for API calls
