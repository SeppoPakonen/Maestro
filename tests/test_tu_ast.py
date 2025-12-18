import os
import tempfile
from pathlib import Path

from maestro.tu.ast_nodes import SourceLocation, Symbol, ASTNode, ASTDocument
from maestro.tu.serializer import ASTSerializer
from maestro.tu.clang_parser import ClangParser
from maestro.tu.errors import ParserUnavailableError


def test_ast_round_trip():
    loc = SourceLocation(file="test.c", line=10, column=5)
    sym = Symbol(name="my_var", kind="variable", loc=loc)
    child_node = ASTNode(kind="var_decl", name="x", loc=loc)
    root_node = ASTNode(
        kind="function",
        name="main",
        loc=loc,
        children=[child_node],
        symbol_refs=[sym],
    )
    original_doc = ASTDocument(root=root_node, symbols=[sym])

    data = original_doc.to_dict()
    reconstructed_doc = ASTDocument.from_dict(data)

    assert reconstructed_doc.root.kind == "function"
    assert reconstructed_doc.root.name == "main"
    assert len(reconstructed_doc.root.children or []) == 1
    assert len(reconstructed_doc.root.symbol_refs or []) == 1
    assert reconstructed_doc.root.symbol_refs[0].name == "my_var"


def test_ast_walk_order():
    loc = SourceLocation(file="test.c", line=1, column=1)
    child1 = ASTNode(kind="stmt", name="a", loc=loc)
    child2 = ASTNode(kind="stmt", name="b", loc=loc)
    grandchild = ASTNode(kind="expr", name="c", loc=loc)
    child2.children = [grandchild]
    root = ASTNode(kind="func", name="f", loc=loc, children=[child1, child2])

    nodes = list(root.walk())
    kinds = [n.kind for n in nodes]
    names = [n.name for n in nodes]

    assert kinds == ["func", "stmt", "stmt", "expr"]
    assert names == ["f", "a", "b", "c"]


def test_serializer_round_trip():
    loc = SourceLocation(file="test.c", line=5, column=10)
    sym = Symbol(name="v", kind="var", loc=loc)
    node = ASTNode(kind="decl", name="var_v", loc=loc, symbol_refs=[sym])
    doc = ASTDocument(root=node, symbols=[sym])

    json_str = ASTSerializer.to_json(doc)
    reconstructed_doc = ASTSerializer.from_json(json_str)

    assert reconstructed_doc.root.kind == "decl"
    assert reconstructed_doc.root.name == "var_v"
    assert len(reconstructed_doc.symbols) == 1
    assert reconstructed_doc.symbols[0].name == "v"


def test_clang_parser_availability():
    try:
        import clang.cindex  # noqa: F401
        has_clang = True
    except ImportError:
        has_clang = False

    if not has_clang:
        try:
            ClangParser()
        except ParserUnavailableError:
            return
        raise AssertionError("Expected ParserUnavailableError when clang.cindex is missing")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as temp:
        temp.write("int main() { int x = 5; return 0; }\n")
        temp_path = Path(temp.name)

    try:
        parser = ClangParser()
        doc = parser.parse_file(temp_path)
        assert doc.root.kind.lower().startswith("translation_unit")
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    test_ast_round_trip()
    test_ast_walk_order()
    test_serializer_round_trip()
    test_clang_parser_availability()
    print("All tests passed!")
