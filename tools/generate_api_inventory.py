import json
import csv
import re
from pathlib import Path
import javalang

SRC_ROOT = Path('src/main/java')
OUTPUT_DIR = Path('inventory_v2')
OUTPUT_DIR.mkdir(exist_ok=True)

packages = set()
interfaces = []
abstract_classes = []
concrete_classes = []
enums = []
events = []
capability_hints = []
reactor_blueprint_hints = []

method_catalog_rows = []

DOMAIN_MAP = {
    'ic2.api.energy': 'energy',
    'ic2.api.reactor': 'reactor',
    'ic2.api.tiles': 'tiles',
    'ic2.api.items': 'items',
    'ic2.api.network': 'network',
    'ic2.api.recipes': 'recipes',
    'ic2.api.events': 'events',
}

def detect_domain(pkg):
    for prefix, domain in DOMAIN_MAP.items():
        if pkg == prefix or pkg.startswith(prefix + '.'):
            return domain
    return 'other'


def preprocess_source(source):
    # Handle Java pattern matching for instanceof used in conjunction with &&
    pattern_and = re.compile(r'(?P<expr>[A-Za-z0-9_\.()]+)\s+instanceof\s+(?P<type>[A-Za-z0-9_$.]+)\s+(?P<var>[A-Za-z0-9_]+)\s*&&\s*(?P=var)(?P<tail>[^;]+)')

    def repl_and(match):
        expr = match.group('expr')
        type_name = match.group('type')
        tail = match.group('tail')
        return f"{expr} instanceof {type_name} && (({type_name}) {expr}){tail}"

    source = pattern_and.sub(repl_and, source)

    # Handle ternary pattern matching: expr instanceof Type var ? var : other
    pattern_ternary = re.compile(r'(?P<expr>[A-Za-z0-9_\.()]+)\s+instanceof\s+(?P<type>[A-Za-z0-9_$.]+)\s+(?P<var>[A-Za-z0-9_]+)\s*\?\s*(?P=var)\s*:\s*')

    def repl_ternary(match):
        expr = match.group('expr')
        type_name = match.group('type')
        return f"{expr} instanceof {type_name} ? ({type_name}) {expr} : "

    source = pattern_ternary.sub(repl_ternary, source)

    # Replace method references like Type[]::new used in toArray calls with array constructors.
    pattern_array_ctor = re.compile(r'toArray\(\s*([A-Za-z0-9_$.]+)\[\]\s*::\s*new\s*\)')

    def repl_array_ctor(match):
        type_name = match.group(1)
        return f"toArray(new {type_name}[0])"

    source = pattern_array_ctor.sub(repl_array_ctor, source)

    return source


def strip_comments(source):
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    source = re.sub(r'//.*', '', source)
    return source


def fallback_interface_parse(source, pkg, rel_path):
    text = strip_comments(source)
    match = re.search(r'public\s+interface\s+(?P<name>[A-Za-z0-9_]+)', text)
    if not match:
        return
    name = match.group('name')
    fqcn = f"{pkg}.{name}" if pkg else name
    body_start = text.find('{', match.end())
    if body_start == -1:
        return
    body = text[body_start + 1:]
    sentinel = body.find('class ')
    if sentinel != -1:
        body = body[:sentinel]
    methods = []
    constants = []
    buffer = []
    depth = 0
    for ch in body:
        if ch == '{':
            depth += 1
        elif ch == '}':
            if depth == 0:
                break
            depth -= 1
        buffer.append(ch)
    statements = ''.join(buffer).split(';')
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        if '(' in stmt and ')' in stmt and not stmt.startswith('class '):
            if stmt.strip().startswith(('for', 'if', 'while', 'switch')):
                continue
            signature = stmt.replace('\n', ' ')
            signature = re.sub(r'\s+', ' ', signature)
            signature = signature + ';'
            method_name = signature.split('(')[0].split()[-1]
            methods.append({
                'name': method_name,
                'sig': signature,
                'notes': 'DECLARED (fallback)',
            })
            method_catalog_rows.append((detect_domain(pkg), fqcn, method_name, 'method', signature, 'DECLARED (fallback)'))
        elif '=' in stmt:
            parts = stmt.split('=')
            left = parts[0].strip().split()
            if left:
                name_part = left[-1]
                type_part = ' '.join(left[:-1])
                method_catalog_rows.append((detect_domain(pkg), fqcn, name_part, 'field', f"{type_part} {name_part}", 'unknown'))
                constants.append({
                    'name': name_part,
                    'value': 'unknown',
                    'notes': 'DECLARED (fallback)',
                })

    interfaces.append({
        'fqcn': fqcn,
        'methods': methods,
        'constants': constants,
        'related': [],
        'domain': detect_domain(pkg),
        'source': str(rel_path),
    })


def type_kind(node):
    if isinstance(node, javalang.tree.ClassDeclaration):
        if 'abstract' in (node.modifiers or []):
            return 'abstract'
        return 'class'
    if isinstance(node, javalang.tree.InterfaceDeclaration):
        return 'interface'
    if isinstance(node, javalang.tree.EnumDeclaration):
        return 'enum'
    return 'other'


def type_to_str(t):
    if t is None:
        return 'void'
    if isinstance(t, str):
        return t
    if isinstance(t, javalang.tree.BasicType):
        result = t.name
        if t.dimensions:
            result += '[]' * len(t.dimensions)
        return result
    if isinstance(t, javalang.tree.ReferenceType):
        result = '.'.join(t.name.parts) if hasattr(t.name, 'parts') else t.name
        if t.arguments:
            args = []
            for arg in t.arguments:
                if isinstance(arg, javalang.tree.TypeArgument):
                    arg_type = getattr(arg, 'type', None)
                    kind = getattr(arg, 'kind', None)
                    if kind == 'extends' and arg_type is not None:
                        args.append(f"? extends {type_to_str(arg_type)}")
                    elif kind == 'super' and arg_type is not None:
                        args.append(f"? super {type_to_str(arg_type)}")
                    elif arg_type is not None:
                        args.append(type_to_str(arg_type))
                    else:
                        args.append('?')
                else:
                    args.append(type_to_str(arg))
            result += '<' + ', '.join(args) + '>'
        if t.dimensions:
            result += '[]' * len(t.dimensions)
        return result
    if hasattr(t, 'name'):
        return t.name
    return str(t)


def format_parameter(param):
    param_type = type_to_str(param.type)
    if param.varargs:
        param_type += '...'
    return f"{param_type} {param.name}"


def get_constant_value(decl):
    init = decl.initializer
    if init is None:
        return 'unknown'
    if isinstance(init, javalang.tree.Literal):
        return init.value
    if isinstance(init, javalang.tree.MemberReference):
        return init.member
    if isinstance(init, javalang.tree.MethodInvocation):
        return init.member + '()'
    if isinstance(init, javalang.tree.Cast):
        return f"({type_to_str(init.type)})"
    return 'unknown'


def type_refs_to_names(type_refs):
    if not type_refs:
        return []
    names = []
    for ref in type_refs:
        if isinstance(ref, javalang.tree.Type):
            names.append(type_to_str(ref))
        elif hasattr(ref, 'name'):
            names.append(type_to_str(ref))
        else:
            names.append(str(ref))
    return names


def record_method(domain, fqcn, method):
    params = ', '.join(format_parameter(p) for p in method.parameters)
    ret = type_to_str(method.return_type)
    signature = f"{ret} {method.name}({params})"
    method_catalog_rows.append((domain, fqcn, method.name, 'method', signature, 'DECLARED'))
    return signature


def record_field(domain, fqcn, field, declarator):
    type_name = type_to_str(field.type)
    name = declarator.name
    value = get_constant_value(declarator)
    method_catalog_rows.append((domain, fqcn, name, 'field', f"{type_name} {name}", value))
    return value


for path in sorted(SRC_ROOT.rglob('*.java')):
    rel_path = path.relative_to(SRC_ROOT)
    with path.open('r', encoding='utf-8') as fh:
        source = preprocess_source(fh.read())
    try:
        tree = javalang.parse.parse(source)
    except (javalang.parser.JavaSyntaxError, IndexError) as exc:
        print(f"Failed to parse {rel_path}: {exc}")
        fallback_interface_parse(source, pkg, rel_path)
        continue

    pkg = tree.package.name if tree.package else ''
    if pkg:
        packages.add(pkg)
    domain = detect_domain(pkg)

    for type_decl in tree.types:
        fqcn = f"{pkg}.{type_decl.name}" if pkg else type_decl.name
        kind = type_kind(type_decl)

        if kind == 'enum':
            values = [const.name for const in getattr(type_decl.body, 'constants', [])]
            enums.append({
                'fqcn': fqcn,
                'values': values,
                'domain': domain,
            })
            method_catalog_rows.append((domain, fqcn, type_decl.name, 'enum', ','.join(values), ''))
        elif kind == 'interface':
            methods = []
            constants = []
            for field in type_decl.fields:
                for declarator in field.declarators:
                    value = record_field(domain, fqcn, field, declarator)
                    constants.append({
                        'name': declarator.name,
                        'value': value,
                        'notes': 'DECLARED',
                    })
            for method in type_decl.methods:
                signature = record_method(domain, fqcn, method)
                methods.append({
                    'name': method.name,
                    'sig': signature,
                    'notes': 'DECLARED',
                })
            interfaces.append({
                'fqcn': fqcn,
                'methods': methods,
                'constants': constants,
                'related': type_refs_to_names(type_decl.extends),
                'domain': domain,
            })
        elif kind in {'abstract', 'class'}:
            methods = []
            constants = []
            for field in type_decl.fields:
                if any(mod in {'public', 'protected'} for mod in (field.modifiers or [])):
                    for declarator in field.declarators:
                        value = record_field(domain, fqcn, field, declarator)
                        constants.append({
                            'name': declarator.name,
                            'value': value,
                            'notes': 'DECLARED',
                        })
            for method in type_decl.methods:
                if any(mod in {'public', 'protected', 'abstract'} for mod in (method.modifiers or [])):
                    signature = record_method(domain, fqcn, method)
                    methods.append({
                        'name': method.name,
                        'sig': signature,
                        'notes': 'DECLARED',
                    })
            class_entry = {
                'fqcn': fqcn,
                'methods': methods,
                'constants': constants,
                'related': sorted(set(type_refs_to_names(type_decl.extends) + type_refs_to_names(type_decl.implements))),
                'domain': domain,
            }
            if kind == 'abstract':
                abstract_classes.append(class_entry)
            else:
                concrete_classes.append(class_entry)

        if pkg.startswith('ic2.api.events') and isinstance(type_decl, javalang.tree.ClassDeclaration):
            fields = []
            for field in type_decl.fields:
                if 'public' in (field.modifiers or []):
                    for decl in field.declarators:
                        fields.append({'name': decl.name, 'type': type_to_str(field.type)})
            events.append({
                'fqcn': fqcn,
                'fields': fields,
                'when': 'INFERRED',
            })

        if 'Planner' in type_decl.name or 'Simulated' in type_decl.name or 'Tracker' in type_decl.name:
            reactor_blueprint_hints.append({
                'class': fqcn,
                'hint': 'INFERRED planner/simulated/tracker role from name',
            })

    if 'ForgeCapabilities' in source:
        capability_hints.append({
            'name': 'ForgeCapabilities',
            'source': str(rel_path),
            'notes': 'DECLARED reference in source',
        })

packages = sorted(packages)

api_contracts = {
    'packages': packages,
    'interfaces': interfaces,
    'abstract_classes': abstract_classes,
    'enums': enums,
    'events': events,
    'capability_hints': capability_hints,
    'reactor_blueprint_hints': reactor_blueprint_hints,
}

with (OUTPUT_DIR / 'api_contracts.json').open('w', encoding='utf-8') as fh:
    json.dump(api_contracts, fh, indent=2)

with (OUTPUT_DIR / 'method_catalog.csv').open('w', encoding='utf-8', newline='') as fh:
    writer = csv.writer(fh)
    writer.writerow(['domain', 'fqcn', 'member', 'kind', 'signature_or_value', 'notes'])
    for row in method_catalog_rows:
        writer.writerow(row)
