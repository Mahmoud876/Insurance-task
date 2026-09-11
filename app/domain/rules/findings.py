from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class RuleFinding:
    code:str 
    message:str 
    field_name :str 
    #the actual value that caused the finding
    raw_value : Any =None 
    severity :str ="ERROR"

    def as_dict(self)->dict[str,Any]:
        return {
            "code":self.code,
            "message":self.message,
            "field_name":self.field_name,
            "raw_value":self.raw_value,
            "severity":self.severity
        }
    