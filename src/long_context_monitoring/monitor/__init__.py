"""Score archived Claude and Codex transcripts for suspicious behavior.

The monitor extracts native events, filters them by visibility, renders the
visible trajectory, and scores the chosen strategy's views. The prompt follows
ControlArena's basic-monitor convention. Each result records its configuration,
prompt hashes, scores, and reasoning.
"""
