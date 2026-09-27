from pydantic import BaseModel, ConfigDict


class DocFactoryModel(BaseModel):
    """Base class of every docFactory model: a field that is not declared is a validation error."""

    model_config = ConfigDict(extra="forbid")
