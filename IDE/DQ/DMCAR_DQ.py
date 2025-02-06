from enum import Enum
from pandas import isna

class FunctionScope(Enum):
    FIRST=1
    ALL=2

class Function():
    def __init__(self):
        pass

    def __call__(self, parms=None) -> bool:
        print ("Function not implemented")
    
    def on_fail_msg(self) -> str:
        return "{dqtest} fail".format(dqtest=self.name)


class dq_fail(Function):
    name = "dq_fail"
    description = "A test function that always fails"
    scope=FunctionScope.ALL

    def __call__(self, row):
        return False

class dq_all_DMCAR_fields_present(Function):
    name = "dq_all_DMCAR_fields_present"
    description = "Tests that all expected column-names are present in the row-header definition"
    scope=FunctionScope.FIRST
    expectedfieldset = {"Namespace",
                        "NamespaceLabel",
                        "NamespaceDescription",
                        "Domain",
                        "DomainLabel",
                        "DomainDescription",
                        "ParentDomain",
                        "DomainEvent",
                        "DomainEventLabel",
                        "DomainEventDescription",
                        "DomainParticipant",
                        "DomainParticipantLabel",	
                        "DomainParticipantDescription",	
                        "Model",	
                        "ModelLabel",	
                        "ModelDescription",	
                        "ModelType",
                        "Class"	,
                        "ClassLabel",
                        "ClassDescription",
                        "Attribute",
                        "AttributeLabel",
                        "AttributeDescription",
                        "Sequence",
                        "DataType",
                        "Nulls",	
                        "IsPK",
                        "Relationship",
                        "RelationshipLabel",
                        "RelationshipDescription",
                        "RelationshipType",	
                        "FromNamespace",
                        "FromClass",
                        "FromAttribute",
                        "FromCardinality",
                        "ToNamespace",
                        "ToClass",
                        "ToAttribute",	
                        "ToCardinality"}
    
    def __call__(self, row):
        
        if set(row.keys())==self.expectedfieldset:
            return True
        else:
            return False
    

class dq_namespace_is_populated(Function):
    name = "dq_namespace_is_populated"
    description = "Namespace must be populated"
    scope=FunctionScope.ALL

    def __call__(self, row):
        if str(row.get("Namespace")).strip() == "" or isna(row.get("Namespace")):
            return False
        else:
            return True
        

class dq_class_label_population_requires_class_is_populated(Function):
    name = "dq_class_label_population_requires_class_is_populated"
    description = "Class label should be populated if class is populated"
    scope=FunctionScope.ALL

    def __call__(self, row):
        if not isna(row.get("ClassLabel")):
            return False
        else:
            return True
        
