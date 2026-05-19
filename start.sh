#!/bin/bash
trap 'trap - INT TERM EXIT; kill -TERM 0 2>/dev/null; wait 2>/dev/null; exit' INT TERM EXIT

uv run main.py
