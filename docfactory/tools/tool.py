import inspect
from typing import Any, Callable

from pydantic import BaseModel, ValidationError, create_model


class Tool:
    """One function tool: a plain typed Python function plus the name and description an LLM sees.

    The argument schema is derived from the function signature (Annotated types carrying Field descriptions), so the
    same typed function is the validator, the LLM tool schema and the documentation. No business logic lives here.
    """

    def __init__(self, func: Callable[..., Any], description: str, name: str | None = None) -> None:
        self.func = func
        self.name = name or func.__name__
        self.description = description
        parameters = inspect.signature(func, eval_str=True).parameters
        fields = {n: (p.annotation, ... if p.default is inspect.Parameter.empty else p.default) for n, p in parameters.items()}
        self.args_model: type[BaseModel] = create_model(f"{self.name}_arguments", **fields)

    def input_schema(self) -> dict:
        """JSON schema of the arguments, derived from the function's typed signature."""
        schema = self.args_model.model_json_schema()
        schema.pop("title", None)
        return schema

    def call(self, arguments: dict) -> Any:
        """Validate `arguments`, run the function and return a JSON-compatible result.

        Bad arguments and operational errors (ValueError, FileNotFoundError) come back as {"ok": false, "error": ...}
        so the caller can fix the call; they never raise.
        """
        try:
            validated = self.args_model(**arguments)
            result = self.func(**{name: getattr(validated, name) for name in self.args_model.model_fields})
        except ValidationError as exc:
            return {"ok": False, "error": "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())}
        except (ValueError, FileNotFoundError) as exc:
            return {"ok": False, "error": str(exc)}
        return _jsonable(result)


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value
