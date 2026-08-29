from pydantic import BaseModel
import dataclasses

@dataclasses.dataclass
class MyModel:
    id: int
    name: str

class MyResponse(BaseModel):
    id: int
    name: str

# FastAPI automatically does this validation internally:
m = MyModel(id=1, name="test")
r = MyResponse.model_validate(m, from_attributes=True)
print(r)
