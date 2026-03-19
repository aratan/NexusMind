---
name: skill-factory
description: A factory for creating other Agent Skills. It uses Qwen3.5 via Ollama to generate the structure and content of new skills based on a description. Use this when you need to expand your capabilities or create specialized tools.
license: MIT
metadata:
  author: Antigravity
  version: "1.0"
  model: qwen3.5
  provider: ollama
---

# Skill Factory

This skill allows an agent to create new skills following the [Agent Skills standard](https://agentskills.io/).

## How to use

1. Identify a need for a new skill (e.g., "I need a skill to analyze CSV files").
2. Run the `create_skill.py` script with the description of the skill.
3. The script will generate a new directory in the `skills/` folder with:
   - `SKILL.md`: Main instructions and metadata.
   - `scripts/`: Implementation scripts if needed.
   - `references/`: Documentation.
   - `assets/`: Templates or static files.

## Command

```bash
python skills/skill-factory/scripts/create_skill.py "description of the skill"
```

## Requirements

- Python 3.x
- Ollama running locally with `qwen3.5:latest` model.
- `requests` library installed (`pip install requests`).
