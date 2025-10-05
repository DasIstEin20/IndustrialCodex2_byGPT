#!/usr/bin/env python3
import csv
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import javalang

SRC_ROOT = Path('src/main/java')
OUT_DIR = Path('inventory_v2')

DOMAIN_MAP = {
    'ic2.api.energy': 'energy',
    'ic2.api.reactor': 'reactor',
    'ic2.api.tiles': 'tiles',
    'ic2.api.items': 'items',
    'ic2.api.network': 'network',
    'ic2.api.recipes': 'recipes',
    'ic2.api.events': 'events',
}


def classify_domain(pkg: str) -> str:
    for prefix, domain in DOMAIN_MAP.items():
        if pkg == prefix or pkg.startswith(prefix + '.'):
            return domain
    return 'other'


def camel_to_words(name: str) -> str:
    words = re.sub('([a-z])([A-Z])', r'\1 \2', name)
    words = words.replace('_', ' ')
    return words.lower()


@dataclass
class MethodInfo:
    name: str
    return_type: str
    parameters: List[Tuple[str, str]]
    modifiers: List[str]
    throws: List[str]

    def signature(self) -> str:
        params = ', '.join(f"{ptype} {pname}".strip() for ptype, pname in self.parameters)
        throws_part = ''
        if self.throws:
            throws_part = ' throws ' + ', '.join(self.throws)
        return f"{self.return_type} {self.name}({params}){throws_part}".strip()


@dataclass
class FieldInfo:
    name: str
    type: str
    modifiers: List[str]
    value: Optional[str] = None

    def signature(self) -> str:
        if self.value is None:
            return f"{self.type} {self.name}"
        return f"{self.type} {self.name} = {self.value}"


@dataclass
class TypeInfo:
    package: str
    name: str
    kind: str  # interface, class, enum
    modifiers: List[str]
    extends: List[str] = field(default_factory=list)
    implements: List[str] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    fields: List[FieldInfo] = field(default_factory=list)
    enum_constants: List[str] = field(default_factory=list)
    domain: str = 'other'
    path: Path = Path()

    @property
    def fqcn(self) -> str:
        if self.package:
            return f"{self.package}.{self.name}"
        return self.name

    @property
    def is_abstract(self) -> bool:
        return 'abstract' in self.modifiers


class Parser:
    def __init__(self, src_root: Path):
        self.src_root = src_root
        self.types: Dict[str, TypeInfo] = {}
        self.packages: set[str] = set()
        self.parse_errors: List[Tuple[Path, str]] = []

    def parse_all(self) -> None:
        for path in sorted(self.src_root.rglob('*.java')):
            self._parse_file(path)

    def _parse_file(self, path: Path) -> None:
        text = path.read_text(encoding='utf-8')
        try:
            tree = javalang.parse.parse(text)
        except Exception as exc:
            self.parse_errors.append((path, str(exc)))
            return

        pkg = tree.package.name if tree.package else ''
        imports = {}
        for imp in tree.imports:
            simple = imp.path.split('.')[-1]
            imports[simple] = imp.path
        self.packages.add(pkg)

        for type_decl in tree.types:
            self._handle_type(type_decl, pkg, path, imports)

    def _handle_type(self, type_decl, pkg: str, path: Path, imports: Dict[str, str]) -> None:
        if not hasattr(type_decl, 'name'):
            return
        name = type_decl.name
        kind = 'class'
        if isinstance(type_decl, javalang.tree.InterfaceDeclaration):
            kind = 'interface'
        elif isinstance(type_decl, javalang.tree.EnumDeclaration):
            kind = 'enum'
        modifiers = sorted(type_decl.modifiers or [])
        domain = classify_domain(pkg)
        info = TypeInfo(
            package=pkg,
            name=name,
            kind=kind,
            modifiers=modifiers,
            domain=domain,
            path=path,
        )

        def resolve_type(typ) -> Optional[str]:
            if typ is None:
                return None
            if hasattr(typ, 'name'):
                name = typ.name
                if getattr(typ, 'qualifier', None):
                    return f"{typ.qualifier}.{name}"
                if name in imports:
                    return imports[name]
                if pkg:
                    return f"{pkg}.{name}"
                return name
            if isinstance(typ, str):
                return typ
            return None

        if hasattr(type_decl, 'extends'):  # class extends
            extends = type_decl.extends
            if isinstance(extends, list):
                info.extends = [resolve_type(e) or getattr(e, 'name', '') for e in extends]
            elif extends:
                info.extends = [resolve_type(extends) or getattr(extends, 'name', '')]
        if hasattr(type_decl, 'implements') and type_decl.implements:
            info.implements = [resolve_type(impl) or getattr(impl, 'name', '') for impl in type_decl.implements]
        body_members = []
        if isinstance(type_decl, javalang.tree.EnumDeclaration):
            enum_body = type_decl.body
            if enum_body and getattr(enum_body, 'constants', None):
                info.enum_constants = [const.name for const in enum_body.constants]
            if enum_body and getattr(enum_body, 'declarations', None):
                body_members = list(enum_body.declarations)
        else:
            body_members = list(type_decl.body or [])

        # process members
        for body_decl in body_members:
            if isinstance(body_decl, javalang.tree.MethodDeclaration):
                modifiers = sorted(body_decl.modifiers or [])
                if info.kind == 'interface' or 'public' in modifiers:
                    params = []
                    for param in body_decl.parameters:
                        param_type = param.type
                        ptype = resolve_type(param_type) or getattr(param_type, 'name', '')
                        pname = param.name
                        if param.varargs:
                            ptype = (ptype or '') + '...'
                        dimensions = getattr(param_type, 'dimensions', None)
                        if dimensions:
                            ptype = (ptype or '') + '[]' * len(dimensions)
                        params.append((ptype or '', pname))
                    return_type = ''
                    if body_decl.return_type:
                        return_type = resolve_type(body_decl.return_type) or getattr(body_decl.return_type, 'name', '')
                    else:
                        return_type = 'void'
                    throws = [resolve_type(t) or getattr(t, 'name', '') for t in (body_decl.throws or [])]
                    method_info = MethodInfo(
                        name=body_decl.name,
                        return_type=return_type,
                        parameters=params,
                        modifiers=modifiers,
                        throws=throws,
                    )
                    info.methods.append(method_info)
            elif isinstance(body_decl, javalang.tree.FieldDeclaration):
                modifiers = sorted(body_decl.modifiers or [])
                if 'public' in modifiers:
                    ftype = resolve_type(body_decl.type) or getattr(body_decl.type, 'name', '')
                    for declarator in body_decl.declarators:
                        value = None
                        if declarator.initializer is not None:
                            value = stringify_expression(declarator.initializer)
                        field_info = FieldInfo(
                            name=declarator.name,
                            type=ftype or '',
                            modifiers=modifiers,
                            value=value,
                        )
                        info.fields.append(field_info)
        self.types[info.fqcn] = info


_LITERAL_ATTRS = {
    'value',
}


def stringify_expression(node) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, javalang.tree.Literal):
        return node.value
    if isinstance(node, javalang.tree.MemberReference):
        parts = []
        if node.qualifier:
            parts.append(node.qualifier)
        parts.append(node.member)
        return '.'.join(parts)
    if isinstance(node, javalang.tree.BinaryOperation):
        left = stringify_expression(node.operandl)
        right = stringify_expression(node.operandr)
        return f"{left} {node.operator} {right}"
    if isinstance(node, javalang.tree.Cast):
        typ = stringify_expression(node.type)
        expr = stringify_expression(node.expression)
        return f"(({typ}) {expr})"
    if isinstance(node, javalang.tree.TernaryExpression):
        cond = stringify_expression(node.condition)
        if_true = stringify_expression(node.if_true)
        if_false = stringify_expression(node.if_false)
        return f"{cond} ? {if_true} : {if_false}"
    if isinstance(node, javalang.tree.MethodInvocation):
        args = ', '.join(filter(None, [stringify_expression(a) for a in node.arguments]))
        parts = []
        if node.qualifier:
            parts.append(node.qualifier)
        parts.append(f"{node.member}({args})")
        return '.'.join(parts)
    if isinstance(node, javalang.tree.ClassReference):
        return f"{node.type.name}.class"
    if isinstance(node, javalang.tree.ArrayInitializer):
        values = ', '.join(filter(None, [stringify_expression(v) for v in node.initializers]))
        return '{' + values + '}'
    if isinstance(node, javalang.tree.This):
        return 'this'
    if isinstance(node, javalang.tree.SuperMethodInvocation):
        args = ', '.join(filter(None, [stringify_expression(a) for a in node.arguments]))
        return f"super.{node.member}({args})"
    if isinstance(node, javalang.tree.SuperMemberReference):
        return f"super.{node.member}"
    if isinstance(node, javalang.tree.ArraySelector):
        return f"{stringify_expression(node.primary)}[{stringify_expression(node.index)}]"
    if isinstance(node, javalang.tree.ReferenceType):
        name = node.name
        if node.arguments:
            args = ', '.join(filter(None, [stringify_expression(a) for a in node.arguments]))
            return f"{name}<{args}>"
        return name
    if hasattr(node, 'value'):
        return str(node.value)
    return None


def main():
    parser = Parser(SRC_ROOT)
    parser.parse_all()

    OUT_DIR.mkdir(exist_ok=True)

    # Prepare JSON data structures
    packages = sorted(pkg for pkg in parser.packages if pkg)

    interfaces = []
    abstract_classes = []
    enums = []
    events = []
    capability_hints = []
    reactor_blueprints = []

    method_rows = []

    edges = set()

    for info in sorted(parser.types.values(), key=lambda t: t.fqcn):
        # Build method catalog rows
        for method in info.methods:
            method_rows.append([
                info.domain,
                info.fqcn,
                method.name,
                'method',
                method.signature(),
                'public',
            ])
        for field in info.fields:
            value = field.value if field.value is not None else ''
            method_rows.append([
                info.domain,
                info.fqcn,
                field.name,
                'field',
                field.signature(),
                'public',
            ])
        if info.kind == 'enum':
            enums.append({
                'fqcn': info.fqcn,
                'values': info.enum_constants,
                'domain': info.domain,
            })
            method_rows.append([
                info.domain,
                info.fqcn,
                ','.join(info.enum_constants),
                'enum',
                '|'.join(info.enum_constants),
                'constants',
            ])
        if info.kind == 'interface':
            interfaces.append({
                'fqcn': info.fqcn,
                'methods': [
                    {
                        'name': m.name,
                        'sig': m.signature(),
                        'notes': '',
                    }
                    for m in info.methods
                ],
                'constants': [
                    {
                        'name': f.name,
                        'value': f.value or '',
                        'notes': '',
                    }
                    for f in info.fields
                ],
                'related': sorted(set(info.extends + info.implements)),
                'domain': info.domain,
            })
        elif info.kind == 'class' and info.is_abstract:
            abstract_classes.append({
                'fqcn': info.fqcn,
                'methods': [
                    {
                        'name': m.name,
                        'sig': m.signature(),
                        'notes': '',
                    }
                    for m in info.methods
                ],
                'constants': [
                    {
                        'name': f.name,
                        'value': f.value or '',
                        'notes': '',
                    }
                    for f in info.fields
                ],
                'extends': info.extends,
                'implements': info.implements,
                'domain': info.domain,
            })
        if info.domain == 'events' and info.kind == 'class':
            events.append({
                'fqcn': info.fqcn,
                'fields': [
                    {
                        'name': f.name,
                        'type': f.type,
                    }
                    for f in info.fields
                ],
                'when': '',
            })
        # edges
        for target in info.extends + info.implements:
            if target:
                edges.add((info.fqcn, target, 'extends'))

    # Write method catalog
    method_rows.sort(key=lambda row: (row[1], row[3], row[2]))
    with (OUT_DIR / 'method_catalog.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['domain', 'fqcn', 'member', 'kind', 'signature_or_value', 'notes'])
        for row in method_rows:
            writer.writerow(row)

    # Write api_contracts.json
    api_contracts = {
        'packages': packages,
        'interfaces': interfaces,
        'abstract_classes': abstract_classes,
        'enums': enums,
        'events': events,
        'capability_hints': capability_hints,
        'reactor_blueprint_hints': reactor_blueprints,
    }
    with (OUT_DIR / 'api_contracts.json').open('w', encoding='utf-8') as fh:
        json.dump(api_contracts, fh, indent=2)

    # Mermaid edges
    with (OUT_DIR / 'behavior_edges.mmd').open('w', encoding='utf-8') as fh:
        fh.write('graph TD\n')
        for source, target, relation in sorted(edges):
            fh.write(f"{source.replace('.', '_')} -->|{relation}| {target.replace('.', '_')}\n")

    # Prepare summary skeleton for Markdown
    domain_sections = defaultdict(list)
    for info in sorted(parser.types.values(), key=lambda t: (t.domain, t.fqcn)):
        if info.domain == 'other':
            continue
        lines = []
        header = f"#### {info.fqcn}"
        lines.append(header)
        if info.kind == 'interface':
            lines.append('Type: Interface')
        elif info.kind == 'enum':
            lines.append('Type: Enum')
        else:
            lines.append(f"Type: {'Abstract class' if info.is_abstract else 'Class'}")
        if info.extends:
            lines.append(f"Extends: {', '.join(info.extends)}")
        if info.implements:
            lines.append(f"Implements: {', '.join(info.implements)}")
        if info.fields:
            lines.append('Constants:')
            for field in info.fields:
                description = camel_to_words(field.name)
                if field.value:
                    lines.append(f"- `{field.signature()}` — {description}.")
                else:
                    lines.append(f"- `{field.signature()}` — {description}.")
        if info.methods:
            lines.append('Methods:')
            for method in info.methods:
                description = camel_to_words(method.name)
                lines.append(f"- `{method.signature()}` — {description}.")
        if info.kind == 'enum' and info.enum_constants:
            lines.append('Values: ' + ', '.join(info.enum_constants))
        domain_sections[info.domain].append('\n'.join(lines))

    checklist_defaults = {
        'energy': [
            'Handle directional energy flow (sources, sinks, relays).',
            'Respect reported voltage/tier limits when accepting or emitting EU.',
            'Integrate with the energy net for connectivity queries.',
            'Implement failure handling when energy requests exceed capacity.',
            'Provide thread-safe energy storage updates if used asynchronously.',
        ],
        'reactor': [
            'Track reactor heat and hull heat exchanges accurately per tick.',
            'Respect reactor size (6x9) and chamber adjacency assumptions.',
            'Implement durability/heat damage hooks for components.',
            'Provide EU/tick or heat/tick calculations matching planner expectations.',
            'Expose inventory layout compatible with planner simulations.',
        ],
        'tiles': [
            'Implement item and fluid IO following capability contracts.',
            'Support machine state persistence via NBT or block entity data.',
            'Ensure orientation and facing logic matches wrench interactions.',
            'Respect network synchronization requirements for GUIs.',
            'Handle chunk loading/unloading without duplicating resources.',
        ],
        'items': [
            'Handle electric item charge/discharge in EU units.',
            'Respect tier limits when interacting with energy networks.',
            'Provide tool actions (wrench, scanner, reader) with durability hooks.',
            'Expose tooltip or HUD data readers expect from target blocks.',
            'Integrate with upgrade or transformer interfaces when applicable.',
        ],
        'network': [
            'Register packets on the appropriate channel with matching IDs.',
            'Ensure container synchronization uses thread-safe buffers.',
            'Respect client/server direction when sending updates.',
            'Validate packet data before applying world changes.',
            'Keep protocol version strings in sync between peers.',
        ],
        'recipes': [
            'Register serializers with the expected registry keys.',
            'Validate input stacks and fluid amounts before processing.',
            'Emit recipe outputs deterministically for planner tools.',
            'Support integration with external automation if hooks provided.',
            'Handle recipe removal or replacement via API calls safely.',
        ],
        'events': [
            'Fire events on the main thread unless documented otherwise.',
            'Populate event payloads with immutable data when possible.',
            'Respect cancelability semantics for cancellable events.',
            'Document when events fire to avoid duplicate listeners.',
            'Use Forge event bus registration patterns for subscribers.',
        ],
    }

    with (OUT_DIR / 'API_BEHAVIORS.md').open('w', encoding='utf-8') as fh:
        fh.write('# API Behavior Map\n\n')
        for domain in ['energy', 'reactor', 'tiles', 'items', 'network', 'recipes', 'events']:
            entries = domain_sections.get(domain)
            if not entries:
                continue
            title = domain.capitalize()
            if domain == 'items':
                title = 'Items/Readers/Electric'
            elif domain == 'tiles':
                title = 'Tiles/Tubes/Teleport'
            elif domain == 'energy':
                title = 'Energy/Cables'
            elif domain == 'reactor':
                title = 'Reactor/Planner'
            elif domain == 'network':
                title = 'Network/Buffer/Container'
            elif domain == 'recipes':
                title = 'Recipes/Registries'
            elif domain == 'events':
                title = 'Events'
            fh.write(f"## {title}\n\n")
            for entry in entries:
                fh.write(entry)
                fh.write('\n\n')
            checklist = checklist_defaults.get(domain)
            if checklist:
                fh.write('**Implementation Checklist**\n')
                for item in checklist:
                    fh.write(f"- {item}\n")
                fh.write('\n')

    # Print summary counts
    counts = defaultdict(int)
    for info in parser.types.values():
        counts[info.domain] += 1
    for domain, count in sorted(counts.items()):
        print(f"{domain}: {count}")


if __name__ == '__main__':
    main()
