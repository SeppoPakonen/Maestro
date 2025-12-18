import gzip
import json
from typing import Union

from .ast_nodes import ASTDocument


class ASTSerializer:
    """Serializer for ASTDocument objects."""

    @staticmethod
    def to_json(doc: ASTDocument, *, compress: bool = False) -> Union[str, bytes]:
        data = doc.to_dict()
        json_str = json.dumps(data, indent=2)
        if compress:
            return gzip.compress(json_str.encode('utf-8'))
        return json_str

    @staticmethod
    def from_json(data: Union[str, bytes], *, compress: bool = False) -> ASTDocument:
        if compress:
            json_str = gzip.decompress(data).decode('utf-8')
        else:
            if isinstance(data, bytes):
                json_str = data.decode('utf-8')
            else:
                json_str = data
        parsed_dict = json.loads(json_str)
        return ASTDocument.from_dict(parsed_dict)

    @staticmethod
    def to_bytes(doc: ASTDocument, *, compress: bool = True) -> bytes:
        serialized = ASTSerializer.to_json(doc, compress=compress)
        if isinstance(serialized, bytes):
            return serialized
        return serialized.encode('utf-8')

    @staticmethod
    def from_bytes(data: bytes, *, compress: bool = True) -> ASTDocument:
        return ASTSerializer.from_json(data, compress=compress)
