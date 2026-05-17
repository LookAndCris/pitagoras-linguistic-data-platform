import ast
from collections import Counter
from pathlib import Path


def _duplicate_test_function_names(file_path: Path) -> list[str]:
    module = ast.parse(file_path.read_text(encoding="utf-8"))
    test_names = [
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    counts = Counter(test_names)
    return sorted(name for name, count in counts.items() if count > 1)


def test_document_service_test_names_are_unique() -> None:
    test_file = Path(__file__).parent / "services" / "test_document_service.py"

    duplicates = _duplicate_test_function_names(test_file)

    assert duplicates == [], (
        "Duplicate test function names found in "
        f"{test_file}: {', '.join(duplicates)}"
    )
