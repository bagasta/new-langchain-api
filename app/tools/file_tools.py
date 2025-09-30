import os
import csv
import json
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from app.tools.base import BaseTool


class CSVTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="csv",
            description="Read and write CSV files",
            schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write"],
                        "description": "Action to perform"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to CSV file"
                    },
                    "data": {
                        "type": "array",
                        "description": "Data to write (required for write action)"
                    },
                    "delimiter": {
                        "type": "string",
                        "default": ",",
                        "description": "CSV delimiter"
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding"
                    }
                },
                "required": ["action", "file_path"]
            }
        )

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        action = parameters["action"]
        file_path = parameters["file_path"]

        try:
            if action == "read":
                return self._read_csv(file_path, parameters)
            elif action == "write":
                return self._write_csv(file_path, parameters)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            raise Exception(f"CSV file error: {e}")

    def _read_csv(self, file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        delimiter = parameters.get("delimiter", ",")
        encoding = parameters.get("encoding", "utf-8")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding)

        return {
            "file_path": file_path,
            "data": df.to_dict('records'),
            "columns": df.columns.tolist(),
            "row_count": len(df),
            "encoding": encoding,
            "delimiter": delimiter
        }

    def _write_csv(self, file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        data = parameters["data"]
        delimiter = parameters.get("delimiter", ",")
        encoding = parameters.get("encoding", "utf-8")

        if not data:
            raise ValueError("No data provided for writing")

        df = pd.DataFrame(data)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        df.to_csv(file_path, index=False, sep=delimiter, encoding=encoding)

        return {
            "file_path": file_path,
            "rows_written": len(df),
            "columns": df.columns.tolist(),
            "encoding": encoding,
            "delimiter": delimiter
        }


class JSONTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="json",
            description="Read and write JSON files",
            schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write"],
                        "description": "Action to perform"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to JSON file"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to write (required for write action)"
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding"
                    },
                    "indent": {
                        "type": "integer",
                        "default": 2,
                        "description": "JSON indentation"
                    }
                },
                "required": ["action", "file_path"]
            }
        )

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        action = parameters["action"]
        file_path = parameters["file_path"]

        try:
            if action == "read":
                return self._read_json(file_path, parameters)
            elif action == "write":
                return self._write_json(file_path, parameters)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            raise Exception(f"JSON file error: {e}")

    def _read_json(self, file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        encoding = parameters.get("encoding", "utf-8")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding=encoding) as f:
            data = json.load(f)

        return {
            "file_path": file_path,
            "data": data,
            "encoding": encoding
        }

    def _write_json(self, file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        data = parameters["data"]
        encoding = parameters.get("encoding", "utf-8")
        indent = parameters.get("indent", 2)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        return {
            "file_path": file_path,
            "encoding": encoding,
            "indent": indent
        }


class FileListTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="file_list",
            description="List files in a directory",
            schema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern (e.g., '*.csv', '*.json')"
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "Search recursively"
                    }
                },
                "required": ["directory"]
            }
        )

    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        directory = parameters["directory"]
        pattern = parameters.get("pattern", "*")
        recursive = parameters.get("recursive", False)

        try:
            if not os.path.exists(directory):
                raise FileNotFoundError(f"Directory not found: {directory}")

            if not os.path.isdir(directory):
                raise NotADirectoryError(f"Not a directory: {directory}")

            if recursive:
                files = []
                for root, dirs, filenames in os.walk(directory):
                    for filename in filenames:
                        if self._matches_pattern(filename, pattern):
                            full_path = os.path.join(root, filename)
                            files.append({
                                "path": full_path,
                                "name": filename,
                                "size": os.path.getsize(full_path),
                                "modified": os.path.getmtime(full_path)
                            })
            else:
                files = []
                for filename in os.listdir(directory):
                    if self._matches_pattern(filename, pattern):
                        full_path = os.path.join(directory, filename)
                        if os.path.isfile(full_path):
                            files.append({
                                "path": full_path,
                                "name": filename,
                                "size": os.path.getsize(full_path),
                                "modified": os.path.getmtime(full_path)
                            })

            return {
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "files": files,
                "count": len(files)
            }

        except Exception as e:
            raise Exception(f"File listing error: {e}")

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)