from pathlib import Path

from long_context_monitoring.attack_lab.edits import FunctionEdit, apply_function_edit, verify_function_edit


def test_class_method_replacement_with_multiline_string_verifies(tmp_path: Path) -> None:
    module = tmp_path / "store.py"
    module.write_text(
        '''class Store:
    def query(self) -> str:
        return """
            SELECT value
            FROM records
        """
''',
        encoding="utf-8",
    )
    edit = FunctionEdit(
        path="store.py",
        function="Store.query",
        expected_signature="def query(self) -> str:",
        replacement='''def query(self) -> str:
    marker = "kept"
    return """
        SELECT value
        FROM records
    """
''',
    )

    applied = apply_function_edit(tmp_path, edit)

    assert applied.function_sha256_before != applied.function_sha256_after
    assert verify_function_edit(tmp_path, edit) == (
        True,
        "registered replacement remains present",
    )
