from dataclasses import dataclass, asdict, Field, field, MISSING, fields
from typing import Any, Dict, TypeVar, Type, Callable, get_type_hints, Union, Optional
from enum import Enum
import json
import functools

T = TypeVar('T', bound='Serializable')

def non_serializable(*, repr: bool = False, compare: bool = False):
    """Create a non-serializable field."""
    return field(
        metadata={'non_serializable': True},
        repr=repr,
        compare=compare,
        default=None
    )

@dataclass
class Serializable:
    """Base class for objects that can be serialized to and from dictionaries and JSON."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the object to a dictionary for serialization"""
        def _serialize(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, list):
                return [_serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            elif isinstance(obj, Serializable):
                return obj.to_dict()
            else:
                return obj

        # Get all fields from dataclass
        result = {}
        for f in fields(self):
            # Skip if field is marked as non_serializable
            if f.metadata.get('non_serializable', False):
                continue
            # Skip if field starts with underscore
            if f.name.startswith('_'):
                continue
            # Get the value and serialize it
            value = getattr(self, f.name)
            result[f.name] = _serialize(value)
                
        return result

    def to_json(self) -> str:
        """Convert the object to a JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any], *args, **kwargs) -> T:
        """Create an instance from a dictionary"""
        # Create a copy to avoid modifying input
        data = data.copy()
        
        # Get type hints for proper type conversion
        hints = get_type_hints(cls)
        
        # Convert fields based on their types
        for field_name, field_type in hints.items():
            if field_name in data:
                # Skip non-serializable fields
                field_def = cls.__dataclass_fields__[field_name]
                if field_def.metadata.get('non_serializable', False):
                    continue
                    
                # Convert enums
                if isinstance(field_type, type) and issubclass(field_type, Enum):
                    data[field_name] = field_type(data[field_name])
                # Convert nested Serializable objects
                elif isinstance(field_type, type) and issubclass(field_type, Serializable):
                    if isinstance(data[field_name], dict):
                        data[field_name] = field_type.from_dict(data[field_name])
                        
        # Filter out non-serializable fields
        filtered_data = {
            k: v for k, v in data.items() 
            if k in cls.__dataclass_fields__ and 
            not cls.__dataclass_fields__[k].metadata.get('non_serializable', False)
        }
        
        # Combine all kwargs
        all_kwargs = {**filtered_data, **kwargs}
        
        # Create instance with args and combined kwargs
        return cls(*args, **all_kwargs) 