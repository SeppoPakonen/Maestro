from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Iterator


@dataclass
class SourceLocation:
    file: str
    line: int
    column: int

    def to_dict(self) -> Dict[str, Any]:
        return {'file': self.file, 'line': self.line, 'column': self.column}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceLocation':
        return cls(file=data['file'], line=data['line'], column=data['column'])


@dataclass
class SourceExtent:
    """Start/end range of a node."""
    start: SourceLocation
    end: SourceLocation

    def to_dict(self) -> Dict[str, Any]:
        return {'start': self.start.to_dict(), 'end': self.end.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceExtent':
        return cls(start=SourceLocation.from_dict(data['start']),
                   end=SourceLocation.from_dict(data['end']))


@dataclass
class Symbol:
    name: str
    kind: str
    loc: SourceLocation
    refers_to: Optional[str] = None
    target: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'name': self.name,
            'kind': self.kind,
            'loc': self.loc.to_dict(),
        }
        if self.refers_to is not None:
            result['refers_to'] = self.refers_to
        if self.target is not None:
            result['target'] = self.target
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Symbol':
        loc = SourceLocation.from_dict(data['loc'])
        return cls(
            name=data['name'],
            kind=data['kind'],
            loc=loc,
            refers_to=data.get('refers_to'),
            target=data.get('target'),
        )


@dataclass
class ASTNode:
    kind: str
    name: str
    loc: SourceLocation
    type: Optional[str] = None
    value: Optional[str] = None
    modifiers: Optional[List[str]] = None
    children: Optional[List['ASTNode']] = None
    symbol_refs: Optional[List[Symbol]] = None
    usr: Optional[str] = None
    extent: Optional[SourceExtent] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'kind': self.kind,
            'name': self.name,
            'loc': self.loc.to_dict(),
        }
        if self.type is not None:
            result['type'] = self.type
        if self.value is not None:
            result['value'] = self.value
        if self.modifiers is not None:
            result['modifiers'] = self.modifiers
        if self.children is not None:
            result['children'] = [child.to_dict() for child in self.children]
        if self.symbol_refs is not None:
            result['symbol_refs'] = [sym.to_dict() for sym in self.symbol_refs]
        if self.usr is not None:
            result['usr'] = self.usr
        if self.extent is not None:
            result['extent'] = self.extent.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ASTNode':
        loc = SourceLocation.from_dict(data['loc'])
        children = None
        if 'children' in data:
            children = [ASTNode.from_dict(child_data) for child_data in data['children']]
        symbol_refs = None
        if 'symbol_refs' in data:
            symbol_refs = [Symbol.from_dict(sym_data) for sym_data in data['symbol_refs']]
        usr = data.get('usr')
        extent = None
        if 'extent' in data and data['extent']:
            extent = SourceExtent.from_dict(data['extent'])

        return cls(
            kind=data['kind'],
            name=data['name'],
            loc=loc,
            type=data.get('type'),
            value=data.get('value'),
            modifiers=data.get('modifiers'),
            children=children,
            symbol_refs=symbol_refs,
            usr=usr,
            extent=extent,
        )

    def walk(self) -> Iterator['ASTNode']:
        yield self
        if self.children:
            for child in self.children:
                yield from child.walk()


@dataclass
class ASTDocument:
    root: ASTNode
    symbols: List[Symbol]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'root': self.root.to_dict(),
            'symbols': [sym.to_dict() for sym in self.symbols],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ASTDocument':
        root = ASTNode.from_dict(data['root'])
        symbols = [Symbol.from_dict(sym_data) for sym_data in data['symbols']]
        return cls(root=root, symbols=symbols)
