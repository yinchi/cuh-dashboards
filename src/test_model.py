"""Module defining the simulation model."""

import pydantic as pyd


class TestModel(pyd.BaseModel):
    """Test model."""
    model_config = pyd.ConfigDict(from_attributes=True)

    x: pyd.conint(strict=True, lt=20)

    @staticmethod
    def new(x: int, y: int):
        """new"""
        return TestModel(x=x*y)


ok = TestModel.new(3, 4)
print(ok)
print(type(ok))


try:
    fail = TestModel.new(5, 6)
except pyd.ValidationError as exc:
    print(exc)
