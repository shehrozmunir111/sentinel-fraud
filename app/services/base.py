from abc import ABC, abstractmethod
from typing import Generic, TypeVar

ModelType = TypeVar("ModelType")

class BaseService(ABC, Generic[ModelType]):
    def __init__(self, repository):
        self.repository = repository
    
    @abstractmethod
    async def validate(self, data: dict) -> bool:
        pass