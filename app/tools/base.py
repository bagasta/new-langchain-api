from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time


class BaseTool(ABC):
    def __init__(self, name: str, description: str, schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.schema = schema

    @abstractmethod
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        required_fields = self.schema.get("required", [])
        properties = self.schema.get("properties", {})

        for field in required_fields:
            if field not in parameters:
                raise ValueError(f"Missing required parameter: {field}")

        for field, value in parameters.items():
            if field in properties:
                field_type = properties[field].get("type")
                if field_type and not isinstance(value, self._get_python_type(field_type)):
                    raise ValueError(f"Parameter {field} must be of type {field_type}")

        return True

    def _get_python_type(self, schema_type: str) -> type:
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_map.get(schema_type, object)

    def run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        try:
            self.validate_parameters(parameters)
            result = self.execute(parameters)
            execution_time = time.time() - start_time

            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "error": None
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e)
            }