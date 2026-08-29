from fastapi import FastAPI
from fastapi.testclient import TestClient
import dataclasses
from pydantic import BaseModel
from typing import Any

@dataclasses.dataclass
class MyModel:
    id: int
    name: str

class MyResponse(BaseModel):
    id: int
    name: str

app = FastAPI()

@app.get("/items", response_model=list[MyResponse])
def get_items():
    return [MyModel(id=1, name="test")]

client = TestClient(app)
print(client.get("/items").json())
