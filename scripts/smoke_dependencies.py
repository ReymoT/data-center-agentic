"""Exercise the proposed dependencies offline without implementing domain modules."""

import importlib
import importlib.metadata
import tempfile
from pathlib import Path
from typing import TypedDict

DIRECT = {
    "joblib": "joblib",
    "langgraph": "langgraph",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "pydantic": "pydantic",
    "pyshacl": "pyshacl",
    "pytest": "pytest",
    "pytest-cov": "pytest_cov",
    "python-dotenv": "dotenv",
    "rdflib": "rdflib",
    "ruff": "ruff",
    "scikit-learn": "sklearn",
    "scipy": "scipy",
}


def main():
    for distribution, module in DIRECT.items():
        importlib.import_module(module)
        print(f"IMPORT {distribution} {importlib.metadata.version(distribution)}")

    import joblib
    import numpy as np
    from langgraph.graph import END, START, StateGraph
    from pyshacl import validate
    from rdflib import Graph
    from scipy.optimize import Bounds, LinearConstraint, milp
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier

    data = Graph().parse(
        data="@prefix ex: <urn:smoke:> . ex:item a ex:Item ; ex:value 2 .", format="turtle"
    )
    shapes = Graph().parse(
        data="""@prefix ex: <urn:smoke:> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:Shape a sh:NodeShape ; sh:targetClass ex:Item ;
            sh:property [ sh:path ex:value ; sh:minCount 1 ; sh:datatype xsd:integer ] .""",
        format="turtle",
    )
    assert validate(data, shacl_graph=shapes)[0], "Valid SHACL fixture failed"
    values = list(data.query("SELECT ?v WHERE { <urn:smoke:item> <urn:smoke:value> ?v }"))
    assert len(values) == 1 and int(values[0][0]) == 2, "SPARQL query mismatch"
    invalid = Graph().parse(data="<urn:smoke:item> a <urn:smoke:Item> .", format="turtle")
    assert not validate(invalid, shacl_graph=shapes)[0], "Missing SHACL field passed"
    print("PASS SHACL valid/invalid and SPARQL")

    result = milp(
        c=np.array([1.0, 2.0]),
        integrality=np.ones(2),
        bounds=Bounds(np.zeros(2), np.ones(2)),
        constraints=LinearConstraint([[1.0, 1.0]], [1.0], [1.0]),
    )
    assert result.success and result.status == 0, "Tiny MILP not certified optimal"
    assert np.allclose(result.x, [1, 0]) and abs(result.fun - 1.0) < 1e-9
    print("PASS tiny certified integer program")

    x = [[0, 0], [0, 1], [1, 0], [1, 1]]
    y = [0, 0, 1, 1]
    with tempfile.TemporaryDirectory() as directory:
        for model in (
            DecisionTreeClassifier(random_state=0),
            RandomForestClassifier(n_estimators=10, random_state=0),
        ):
            model.fit(x, y)
            path = Path(directory) / f"{type(model).__name__}.joblib"
            joblib.dump(model, path)
            assert np.array_equal(model.predict(x), joblib.load(path).predict(x))
    print("PASS both classifiers fit/save/load prediction equality")

    class State(TypedDict):
        value: int

    graph = StateGraph(State)
    graph.add_node("increment", lambda state: {"value": state["value"] + 1})
    graph.add_edge(START, "increment")
    graph.add_edge("increment", END)
    assert graph.compile().invoke({"value": 0}) == {"value": 1}
    print("PASS bounded LangGraph route (no provider or model call)")


if __name__ == "__main__":
    main()
