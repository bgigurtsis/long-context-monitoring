"""Parsed-trajectory stand-in for native event ordering and malformed-row contracts."""

from types import SimpleNamespace


class ParsedTrajectory:
    def __init__(self, files, agents=()):
        self.rows = files
        self.agents = list(agents)

    def window(self, file_id, offset, limit, preset="all"):
        return {"entries": self.rows[file_id][offset : offset + limit]}

    def scan(self, file_id):
        return SimpleNamespace(line_count=len(self.rows[file_id]))

    def files(self):
        return {name: {"meta": {"agentPath": name}} for name in self.rows}

    def analysis(self):
        return {"agents": self.agents}


def codex_rows(entries):
    return [
        {"line": line, "entry": {"type": kind, "payload": payload}}
        for line, (kind, payload) in enumerate(entries)
    ]
