# Classification safety improvement plan

## Goal

Improve explainable newsletter classification for internal mail while preserving local-only processing and existing CLI safety contracts.

## Stages

1. Add validated grouping, protection, keyword, and link-metric configuration.
2. Implement explainable grouped scoring and protected-mail decisions.
3. Add evaluation CLI and synthetic labeled fixtures.
4. Run targeted tests, full tests, runtime classification/evaluation checks, and commit.

## Non-goals

No mail retrieval, deletion, external services, persistence, or ML.
