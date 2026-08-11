from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, getcontext
import ast
import math

from apps.study_lab.domain.enums import InstrumentFamily, StudyArtefactOrigin, StudyArtefactType
from apps.study_lab.domain.instruments.schemas import (
    InstrumentSchemaError,
    validate_code_payload,
    validate_comparison_table_payload,
    validate_concept_map_payload,
    validate_diagram_payload,
    validate_equation_payload,
    validate_formula_sheet_payload,
    validate_flashcard_payload,
    validate_graph_payload,
    validate_scratchpad_payload,
    validate_timeline_payload,
)


@dataclass(frozen=True)
class InstrumentResult:
    status: str
    code: str = ""
    result: str = ""
    warnings: tuple[str, ...] = ()


class SafeExpressionError(ValueError):
    pass


class _SafeEvaluator(ast.NodeVisitor):
    base_names = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "pow": pow,
        "abs": abs,
    }

    def __init__(self, variables=None):
        self.allowed_names = dict(self.base_names)
        if variables:
            self.allowed_names.update(variables)

    def visit(self, node):
        return super().visit(node)

    def generic_visit(self, node):
        raise SafeExpressionError("Unsupported expression.")

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return node.value
        raise SafeExpressionError("Unsupported literal.")

    def visit_Name(self, node):
        if node.id in self.allowed_names:
            return self.allowed_names[node.id]
        raise SafeExpressionError("Unknown name.")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise SafeExpressionError("Division by zero.")
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        raise SafeExpressionError("Unsupported operator.")

    def visit_UnaryOp(self, node):
        value = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.USub):
            return -value
        raise SafeExpressionError("Unsupported unary operator.")

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise SafeExpressionError("Unsupported call.")
        func = self.allowed_names.get(node.func.id)
        if func is None:
            raise SafeExpressionError("Unsupported function.")
        args = [self.visit(arg) for arg in node.args]
        return func(*args)


class EvaluateCalculationService:
    @staticmethod
    def execute(expression: str, precision: int = 12, variables=None):
        getcontext().prec = max(precision, 1)
        try:
            normalized = expression.replace("^", "**")
            tree = ast.parse(normalized, mode="eval")
            result = _SafeEvaluator(variables=variables).visit(tree)
            return {"status": "SUCCESS", "expression": expression, "result": str(result), "precision": precision, "warnings": []}
        except ZeroDivisionError:
            return {"status": "INVALID_EXPRESSION", "code": "CALC_DIVISION_BY_ZERO"}
        except (SafeExpressionError, SyntaxError, ValueError, InvalidOperation):
            return {"status": "INVALID_EXPRESSION", "code": "CALC_DOMAIN_ERROR"}


class ConvertUnitService:
    _units = {
        "length": {"m": 1, "cm": Decimal("0.01"), "km": Decimal("1000")},
        "mass": {"g": 1, "kg": Decimal("1000")},
        "time": {"s": 1, "min": Decimal("60"), "h": Decimal("3600")},
        "temperature": {"c": "c", "f": "f", "k": "k"},
    }

    @staticmethod
    def execute(category: str, value: float, source_unit: str, target_unit: str):
        category = category.lower()
        if category not in ConvertUnitService._units:
            return {"status": "INVALID", "code": "UNIT_NOT_SUPPORTED"}
        units = ConvertUnitService._units[category]
        source_unit = source_unit.lower()
        target_unit = target_unit.lower()
        try:
            value = float(value)
        except (TypeError, ValueError):
            return {"status": "INVALID", "code": "UNIT_NOT_SUPPORTED"}
        if source_unit not in units or target_unit not in units:
            return {"status": "INVALID", "code": "UNIT_NOT_SUPPORTED"}
        if category == "temperature":
            c = value
            if source_unit == "f":
                c = (value - 32) * 5 / 9
            elif source_unit == "k":
                c = value - 273.15
            if target_unit == "c":
                return {"status": "SUCCESS", "result": c}
            if target_unit == "f":
                return {"status": "SUCCESS", "result": c * 9 / 5 + 32}
            return {"status": "SUCCESS", "result": c + 273.15}
        base = Decimal(str(value)) * Decimal(str(units[source_unit]))
        result = base / Decimal(str(units[target_unit]))
        return {"status": "SUCCESS", "result": float(result)}


class GenerateGraphDataService:
    @staticmethod
    def execute(expressions, x_min=-10, x_max=10, sample_density=25):
        series = []
        for expression in expressions:
            points = []
            for i in range(sample_density + 1):
                x = x_min + (x_max - x_min) * (i / sample_density)
                result = EvaluateCalculationService.execute(expression, variables={"x": x})
                if result["status"] != "SUCCESS":
                    y = None
                else:
                    try:
                        y = float(result["result"])
                    except ValueError:
                        y = None
                points.append({"x": x, "y": y})
            series.append({"expression": expression, "points": points})
        return {"status": "SUCCESS", "series": series, "viewport": {"x_min": x_min, "x_max": x_max}}


def _create_structured_artefact(*, workspace_id, learner_id, artefact_type, title, summary, payload, visibility="PRIVATE", schema_version="1", provider_context=None, provider_reference="", creation_source="NATIVE"):
    from apps.study_lab.application.interoperability_services import CreateStudyArtefactService

    return CreateStudyArtefactService.execute(
        workspace_id,
        learner_id,
        artefact_type=artefact_type,
        title=title,
        summary=summary,
        provider_context=provider_context,
        provider_reference=provider_reference,
        visibility=visibility,
        schema_version=str(schema_version),
        creation_source=creation_source,
        native_payload=payload,
    )


def _version_structured_artefact(*, workspace_id, learner_id, artefact_id, version, title=None, summary=None, payload=None):
    from apps.study_lab.application.interoperability_services import VersionStudyArtefactService

    return VersionStudyArtefactService.execute(
        workspace_id,
        learner_id,
        artefact_id,
        version=version,
        title=title,
        summary=summary,
        native_payload=payload,
    )


class CreateEquationArtefactService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Equation", summary="", schema_version="1"):
        payload = validate_equation_payload(payload)
        payload.setdefault("authorship", "LEARNER_AUTHORED")
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_type=StudyArtefactType.EQUATION_ARTEFACT,
            title=title,
            summary=summary,
            payload=payload,
            schema_version=schema_version,
        )


class UpdateEquationArtefactService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_equation_payload(payload)
            payload.setdefault("authorship", "LEARNER_AUTHORED")
        return _version_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_id=artefact_id,
            version=version,
            title=title,
            summary=summary,
            payload=payload,
        )


class CreateFormulaSheetService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Formula sheet", summary="", schema_version="1"):
        payload = validate_formula_sheet_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_type=StudyArtefactType.FORMULA_SHEET,
            title=title,
            summary=summary,
            payload=payload,
            schema_version=schema_version,
        )


class UpdateFormulaSheetService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_formula_sheet_payload(payload)
        return _version_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_id=artefact_id,
            version=version,
            title=title,
            summary=summary,
            payload=payload,
        )


class CreateDiagramArtefactService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Diagram", summary="", schema_version="1"):
        payload = validate_diagram_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_type=StudyArtefactType.DIAGRAM_ARTEFACT,
            title=title,
            summary=summary,
            payload=payload,
            schema_version=schema_version,
        )


class CreateGraphArtefactService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Graph", summary="", schema_version="1"):
        payload = validate_graph_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_type=StudyArtefactType.GRAPH_ARTEFACT,
            title=title,
            summary=summary,
            payload=payload,
            schema_version=schema_version,
        )


class ApplyDiagramOperationService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, operation):
        payload = {"operation": operation}
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, payload=payload)


class CreateConceptMapService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Concept map", summary="", schema_version="1"):
        payload = validate_concept_map_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(
            workspace_id=workspace_id,
            learner_id=learner_id,
            artefact_type=StudyArtefactType.CONCEPT_MAP,
            title=title,
            summary=summary,
            payload=payload,
            schema_version=schema_version,
        )


class UpdateConceptMapService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_concept_map_payload(payload)
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, title=title, summary=summary, payload=payload)


class CreateTimelineService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Timeline", summary="", schema_version="1"):
        payload = validate_timeline_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_type=StudyArtefactType.TIMELINE, title=title, summary=summary, payload=payload, schema_version=schema_version)


class UpdateTimelineService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_timeline_payload(payload)
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, title=title, summary=summary, payload=payload)


class CreateComparisonTableService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Comparison table", summary="", schema_version="1"):
        payload = validate_comparison_table_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_type=StudyArtefactType.COMPARISON_TABLE, title=title, summary=summary, payload=payload, schema_version=schema_version)


class UpdateComparisonTableService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_comparison_table_payload(payload)
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, title=title, summary=summary, payload=payload)


class CreateFlashcardSetService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Flashcards", summary="", schema_version="1"):
        payload = validate_flashcard_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_type=StudyArtefactType.FLASHCARD_SET, title=title, summary=summary, payload=payload, schema_version=schema_version)


class AddFlashcardService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, flashcard):
        payload = {"cards": [flashcard]}
        payload = validate_flashcard_payload(payload)
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, payload=payload)


class UpdateFlashcardService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_flashcard_payload(payload)
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, title=title, summary=summary, payload=payload)


class CreateScratchpadService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Scratchpad", summary="", schema_version="1"):
        payload = validate_scratchpad_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_type=StudyArtefactType.SCRATCHPAD_ARTEFACT, title=title, summary=summary, payload=payload, schema_version=schema_version)


class ApplyScratchpadOperationService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, operation):
        payload = {"operation": operation}
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, payload=payload)


class CreateCodeArtefactService:
    @staticmethod
    def execute(workspace_id, learner_id, *, payload, title="Code", summary="", schema_version="1"):
        payload = validate_code_payload(payload)
        payload.setdefault("schema_version", str(schema_version))
        return _create_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_type=StudyArtefactType.CODE_ARTEFACT, title=title, summary=summary, payload=payload, schema_version=schema_version)


class UpdateCodeArtefactService:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id, *, version, payload=None, title=None, summary=None):
        if payload is not None:
            payload = validate_code_payload(payload)
        return _version_structured_artefact(workspace_id=workspace_id, learner_id=learner_id, artefact_id=artefact_id, version=version, title=title, summary=summary, payload=payload)


class ResolveCodeExecutionAvailabilityService:
    @staticmethod
    def execute():
        return {"status": "UNAVAILABLE", "reason_code": "CODE_RUNTIME_NOT_AVAILABLE", "reason_detail": "No secure code runtime is configured."}


class StudyInstrumentProvider:
    def validate_input(self, payload):
        raise NotImplementedError

    def open(self, session, payload):
        raise NotImplementedError

    def resume(self, session, payload):
        raise NotImplementedError

    def apply_operation(self, session, operation):
        raise NotImplementedError

    def produce_artefact(self, session, payload):
        raise NotImplementedError

    def close(self, session, payload=None):
        raise NotImplementedError
