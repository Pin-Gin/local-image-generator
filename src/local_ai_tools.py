from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from json_parts import load_json_part
from local_git_tools import LocalGitTools
from oracle_knowledge_store import OracleKnowledgeStore


TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "git_status": {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Read the current branch and working-tree status of an allowed local Git repository. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {"repo_id": {"type": "string"}},
                "required": ["repo_id"],
            },
        },
    },
    "git_log": {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": "Read recent commits from an allowed local Git repository. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "string"},
                    "max_count": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["repo_id"],
            },
        },
    },
    "git_diff": {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Read a working-tree diff against a ref in an allowed local Git repository. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "string"},
                    "ref": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["repo_id"],
            },
        },
    },
    "git_list_files": {
        "type": "function",
        "function": {
            "name": "git_list_files",
            "description": "List tracked files in an allowed local Git repository. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "string"},
                    "path_prefix": {"type": "string"},
                },
                "required": ["repo_id"],
            },
        },
    },
    "git_read_file": {
        "type": "function",
        "function": {
            "name": "git_read_file",
            "description": "Read a tracked text file from an allowed local Git repository at a specific ref. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "string"},
                    "path": {"type": "string"},
                    "ref": {"type": "string"},
                },
                "required": ["repo_id", "path"],
            },
        },
    },
    "git_search": {
        "type": "function",
        "function": {
            "name": "git_search",
            "description": "Search tracked text files in an allowed local Git repository. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_id": {"type": "string"},
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 200},
                },
                "required": ["repo_id", "query"],
            },
        },
    },
    "knowledge_search": {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": "Search accepted local-AI knowledge in the dedicated Oracle knowledge schema. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
        },
    },
    "json_part_get": {
        "type": "function",
        "function": {
            "name": "json_part_get",
            "description": "Read one exact reusable JSON part by canonical ref such as part:pose.hair-touch@1. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {"ref": {"type": "string"}},
                "required": ["ref"],
            },
        },
    },
}


class LocalAIToolbox:
    def __init__(self, resource_root: Path, config_path: Path) -> None:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("local tools config schema_version must be 1")
        role_tools = payload.get("role_tools")
        if not isinstance(role_tools, dict):
            raise ValueError("local tools role_tools config is missing")
        self.resource_root = resource_root
        self.config = payload
        self.role_tools = role_tools
        self.git = LocalGitTools(resource_root, config_path)
        self.oracle = OracleKnowledgeStore(resource_root)

    def tools_for_role(self, role: str) -> list[dict[str, Any]]:
        names = self.role_tools.get(role, [])
        if not isinstance(names, list):
            raise ValueError(f"local tools role list must be an array: {role}")
        tools: list[dict[str, Any]] = []
        for name in names:
            if not isinstance(name, str) or name not in TOOL_DEFINITIONS:
                raise ValueError(f"unknown local tool configured for role {role}: {name}")
            tools.append(TOOL_DEFINITIONS[name])
        return tools

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "git_status":
            return self.git.status(str(arguments.get("repo_id", "")))
        if name == "git_log":
            return self.git.log(
                str(arguments.get("repo_id", "")),
                max_count=int(arguments.get("max_count", 10)),
            )
        if name == "git_diff":
            return self.git.diff(
                str(arguments.get("repo_id", "")),
                ref=str(arguments.get("ref", "HEAD")),
                path=str(arguments["path"]) if arguments.get("path") is not None else None,
            )
        if name == "git_list_files":
            return self.git.list_files(
                str(arguments.get("repo_id", "")),
                path_prefix=str(arguments.get("path_prefix", "")),
            )
        if name == "git_read_file":
            return self.git.read_file(
                str(arguments.get("repo_id", "")),
                str(arguments.get("path", "")),
                ref=str(arguments.get("ref", "HEAD")),
            )
        if name == "git_search":
            return self.git.search(
                str(arguments.get("repo_id", "")),
                str(arguments.get("query", "")),
                max_results=int(arguments.get("max_results", 50)),
            )
        if name == "knowledge_search":
            return self.oracle.search_knowledge(
                str(arguments.get("query", "")),
                limit=int(arguments.get("limit", 10)),
            )
        if name == "json_part_get":
            ref = str(arguments.get("ref", ""))
            if self.oracle.configured():
                try:
                    indexed = self.oracle.get_json_part(ref)
                except Exception:
                    indexed = None
                if indexed is not None:
                    return {"source": "oracle", **indexed}
            part = load_json_part(self.resource_root, ref)
            return {"source": "file-store", **part.to_request_payload()}
        raise ValueError(f"local AI requested an unavailable tool: {name}")

    def status(self) -> dict[str, Any]:
        oracle_status: dict[str, Any]
        if not self.oracle.configured():
            oracle_status = {"configured": False}
        else:
            try:
                oracle_status = self.oracle.health()
            except Exception as exc:
                oracle_status = {
                    "configured": True,
                    "online": False,
                    "error": str(exc) or exc.__class__.__name__,
                }
        return {
            "git": {
                "read_only": True,
                "configured_repositories": [
                    item.get("repo_id")
                    for item in self.config.get("git", {}).get("repositories", [])
                    if isinstance(item, dict)
                ],
            },
            "oracle": oracle_status,
            "knowledge_store": self.config.get("knowledge_store"),
            "role_tools": self.role_tools,
        }
