from pydantic import BaseModel
from typing import List

class Alias(BaseModel):
    actual_name: str
    alias_name: str
    local_file: bool

class Node(BaseModel):
    type: str
    content: str
    children: List['Node'] = []
    functions: List[str] = []
    aliases: List[Alias] = []