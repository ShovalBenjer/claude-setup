# Knowledge Base

Auto-embedded into `~/.claude/cache/sessions.db` → `knowledge_docs` table.

## Directories

| Dir | Source | Purpose |
|-----|--------|---------|
| `perplexity/` | Perplexity AI research reports (.md/.txt) | Claude skill/rule updates, news-driven learning |
| `devops/` | Azure DevOps CI logs, pipeline JSON exports (.json/.txt) | Self-healing: extract lessons from failures |
| `marketplace/` | Market analysis reports (.md/.txt) | Time-series domain intelligence |
| `marketplace/analysis/` | Auto-generated (by market-analyzer.py) | Do NOT drop files here manually |

## How it works

1. Drop a file in any of the 3 source dirs
2. `knowledge-watch.sh` (inotifywait) detects the change
3. `knowledge-embed.py --file <path>` embeds it via Azure OpenAI
4. Downstream analyzers fire based on source type:
   - `perplexity/` → `skill-updater.sh` (suggests rule/skill changes)
   - `devops/` → `lesson-extractor.py` (writes memory/lesson_*.md)
   - `marketplace/` → `market-analyzer.py` (time-series trend report)

## Scheduled processing

Systemd timer `knowledge-nightly.timer` runs at 02:00 to process any
unembedded files and re-run analyzers.
