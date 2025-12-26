#!/usr/bin/env python3
"""
Maestro v2 Workflow Generator: YAML IR → PlantUML → SVG (LOD0/LOD1/LOD2)

Generates PlantUML diagrams from YAML IR files at multiple levels of detail:
- LOD0: High-level spine (gates + stores only)
- LOD1: Workflow-level (key actions + decisions)
- LOD2: Code-level detail (with callchain from code layer)

Supports both WF (workflow) and CMD (command) diagrams.
"""

import sys
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

# Paths
REPO_ROOT = Path(__file__).resolve().parents[2]
WF_IR_DIR = REPO_ROOT / "docs/workflows/v2/ir/wf"
CMD_IR_DIR = REPO_ROOT / "docs/workflows/v2/ir/cmd"
PUML_OUT_DIR = REPO_ROOT / "docs/workflows/v2/generated/puml"
SVG_OUT_DIR = REPO_ROOT / "docs/workflows/v2/generated/svg"
INDEX_OUT = REPO_ROOT / "docs/workflows/v2/generated/index.md"

# PlantUML command
PLANTUML_CMD = "/usr/bin/plantuml"


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load and validate YAML file."""
    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)
        if not data:
            raise ValueError(f"Empty YAML file: {file_path}")
        return data
    except Exception as e:
        print(f"ERROR: Failed to load {file_path}: {e}", file=sys.stderr)
        sys.exit(1)


def escape_puml(text: str) -> str:
    """Escape special characters for PlantUML."""
    if not text:
        return ""
    # Convert to string if not already
    if not isinstance(text, str):
        text = str(text)
    return text.replace('"', '\\"').replace('\n', '\\n')


def generate_puml_header(title: str, ir_file: str) -> str:
    """Generate PlantUML header with styling."""
    rel_path = Path(ir_file).relative_to(REPO_ROOT)
    return f"""@startuml
!theme plain
skinparam backgroundColor #FFFFFF
skinparam defaultFontName Arial
skinparam ArrowColor #333333
skinparam NoteBorderColor #CCCCCC
skinparam NoteBackgroundColor #FFFFCC

title {escape_puml(title)}

note right
  **Source:** [[{rel_path} {rel_path}]]
end note

"""


def generate_puml_footer() -> str:
    """Generate PlantUML footer."""
    return "\n@enduml\n"


def add_evidence_note(data: Dict[str, Any]) -> str:
    """Generate evidence note with links to v1 documentation."""
    evidence = data.get('evidence', [])
    if not evidence:
        return ""

    note_lines = ["", "note left"]
    note_lines.append("  **Evidence:**")

    for ev in evidence:
        if isinstance(ev, dict):
            path = ev.get('path', '')
            desc = ev.get('description', '')
        else:
            path = str(ev)
            desc = ''

        if path:
            # Make path relative to repo root
            if not path.startswith('v1/') and not path.startswith('docs/'):
                path = f"docs/workflows/{path}"
            link_text = desc if desc else Path(path).name
            note_lines.append(f"  * [[{path} {escape_puml(link_text)}]]")

    note_lines.append("end note")
    return "\n".join(note_lines) + "\n"


def add_ledger_note(data: Dict[str, Any]) -> str:
    """Generate ledger hint note with links."""
    ledger_hints = data.get('ledger_hints', [])
    if not ledger_hints:
        return ""

    note_lines = ["", "note right #FFE6E6"]
    note_lines.append("  **⚠ Ledger Hints:**")

    for hint in ledger_hints:
        note_lines.append(f"  * {escape_puml(hint[:80])}")

    note_lines.append("  ")
    note_lines.append("  [[../../IMPLEMENTATION_LEDGER.md IMPLEMENTATION_LEDGER]]")
    note_lines.append("  [[../../reports/ledger_candidates.md Ledger Candidates]]")
    note_lines.append("end note")
    return "\n".join(note_lines) + "\n"


def add_cmd_jump_points(uses_commands: List[str], lod: int) -> str:
    """Generate jump points to CMD diagrams from WF diagrams."""
    if not uses_commands:
        return ""

    lines = []

    if lod == 0:
        # LOD0: Simple iconic list
        lines.append("")
        lines.append("package \"Uses Commands\" #E6F3FF {")
        for cmd_id in uses_commands:
            cmd_name = cmd_id.replace('CMD-', '')
            svg_link = f"../generated/svg/{cmd_id}.all_layers.lod0.svg"
            lines.append(f'  rectangle "{cmd_name}" as uses_{cmd_name} [[{svg_link}]]')
        lines.append("}")

    elif lod == 1:
        # LOD1: Show chain "WF step → CMD group"
        lines.append("")
        lines.append("package \"Command Integration\" #E6F3FF {")
        for cmd_id in uses_commands:
            cmd_name = cmd_id.replace('CMD-', '')
            svg_link = f"../generated/svg/{cmd_id}.all_layers.lod1.svg"
            lines.append(f'  component "{cmd_name}\\ncommand" as cmd_{cmd_name} [[{svg_link}]]')
        lines.append("}")

    # LOD2: No command callouts (focus on code)

    return "\n".join(lines) + "\n" if lines else ""


def generate_wf_lod0(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD0 PlantUML for WF: spine + gates + stores only."""
    wf_id = data.get('wf_id', 'UNKNOWN')
    title = f"{wf_id} - {data.get('title', 'Untitled')} (LOD0: Spine)"

    puml = generate_puml_header(title, str(ir_file))

    # Start and end nodes
    start_nodes = [n for n in data.get('nodes', []) if n.get('type') == 'start']
    end_nodes = [n for n in data.get('nodes', []) if n.get('type') in ['end', 'exit']]
    gate_nodes = [n for n in data.get('nodes', []) if n.get('type') in ['gate', 'validation', 'decision']]
    hard_stop_nodes = [n for n in data.get('nodes', []) if n.get('type') == 'hard_stop']

    # Add start
    for node in start_nodes:
        puml += f"(*) --> \"{escape_puml(node.get('label', 'Start'))}\"\n"

    # Add gates
    for node in gate_nodes:
        label = escape_puml(node.get('label', node['id']))
        puml += f"if \"{label}\" then\n"
        puml += "  -->[yes] ...\n"
        puml += "  -->[no] ...\n"
        puml += "endif\n"

    # Add hard stops
    for node in hard_stop_nodes:
        label = escape_puml(node.get('label', node['id']))
        puml += f"note right #FF0000\n  **HARD STOP**\\n{label}\nend note\n"

    # Add stores
    stores = data.get('stores', [])
    if stores:
        puml += "\npackage \"Data Stores\" #F0F0F0 {\n"
        for store in stores:
            store_id = store.get('id', 'unknown')
            store_path = store.get('path', '')
            store_format = store.get('format', 'unknown')
            puml += f'  database "{escape_puml(store_id)}\\n{escape_puml(store_path)}" as {store_id}\n'
        puml += "}\n"

    # Add end
    for node in end_nodes:
        puml += f"\"--> (*)\n"

    # Add command jump points
    uses_commands = data.get('uses_commands', [])
    puml += add_cmd_jump_points(uses_commands, lod=0)

    # Add evidence and ledger
    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_wf_lod1(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD1 PlantUML for WF: key actions + decisions."""
    wf_id = data.get('wf_id', 'UNKNOWN')
    title = f"{wf_id} - {data.get('title', 'Untitled')} (LOD1: Workflow)"

    puml = generate_puml_header(title, str(ir_file))

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    # Filter nodes for LOD1 (exclude minor details)
    important_types = ['start', 'end', 'gate', 'action', 'command', 'decision',
                       'validation', 'hard_stop', 'datastore']

    filtered_nodes = [n for n in nodes if n.get('type') in important_types]

    # Add nodes
    for node in filtered_nodes:
        node_id = node['id']
        node_type = node.get('type', 'action')
        label = escape_puml(node.get('label', node_id))

        if node_type == 'start':
            puml += f"(*) --> \"{label}\"\n"
        elif node_type in ['end', 'exit']:
            puml += f"\"{label}\" --> (*)\n"
        elif node_type in ['gate', 'decision', 'validation']:
            puml += f":{label};\n"
        elif node_type == 'hard_stop':
            puml += f"stop\n"
        elif node_type == 'command':
            puml += f":{label}|" + "\n"
        elif node_type == 'datastore':
            puml += f":{label}" + "}\n"
        else:
            puml += f":{label};\n"

    # Add edges (simplified)
    for edge in edges[:20]:  # Limit to first 20 edges for readability
        from_node = edge.get('from', '')
        to_node = edge.get('to', '')
        edge_label = edge.get('label', '')

        if edge_label:
            puml += f"' {from_node} -> {to_node}: {escape_puml(edge_label)}\n"

    # Add command integration
    uses_commands = data.get('uses_commands', [])
    puml += add_cmd_jump_points(uses_commands, lod=1)

    # Add evidence and ledger
    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_wf_lod2(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD2 PlantUML for WF: code detail placeholder."""
    wf_id = data.get('wf_id', 'UNKNOWN')
    title = f"{wf_id} - {data.get('title', 'Untitled')} (LOD2: Code Detail)"

    puml = generate_puml_header(title, str(ir_file))

    puml += "note as N1\n"
    puml += "  **LOD2: Code-level detail**\n"
    puml += "  \n"
    puml += "  This layer shows implementation-level callchains.\n"
    puml += "  Navigate to CMD diagrams for detailed code flows.\n"
    puml += "end note\n"

    # Link to related CMD diagrams
    uses_commands = data.get('uses_commands', [])
    if uses_commands:
        puml += "\npackage \"Implementation Commands\" {\n"
        for cmd_id in uses_commands:
            cmd_name = cmd_id.replace('CMD-', '')
            svg_link = f"../generated/svg/{cmd_id}.code.lod2.svg"
            puml += f'  component "{cmd_name}\\nimplementation" as impl_{cmd_name} [[{svg_link}]]\n'
        puml += "}\n"

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_cmd_cli_lod0(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD0 PlantUML for CMD CLI: basic command structure."""
    cmd_id = data.get('id', 'UNKNOWN')
    title = f"{cmd_id} - {data.get('title', 'Untitled')} (LOD0: CLI Surface)"

    puml = generate_puml_header(title, str(ir_file))

    commands = data.get('commands', [])

    puml += "package \"Command Surface\" {\n"
    for cmd in commands:
        cmd_clean = escape_puml(cmd)
        puml += f'  usecase "{cmd_clean}" as cmd_{commands.index(cmd)}\n'
    puml += "}\n"

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_cmd_cli_lod1(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD1 PlantUML for CMD CLI: command tree with subcommands."""
    cmd_id = data.get('id', 'UNKNOWN')
    title = f"{cmd_id} - {data.get('title', 'Untitled')} (LOD1: CLI Flow)"

    puml = generate_puml_header(title, str(ir_file))

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    # Add nodes
    for node in nodes:
        node_id = node['id']
        node_type = node.get('type', 'command')
        label = escape_puml(node.get('label', node_id))

        if node_type == 'command':
            puml += f'rectangle "{label}" as {node_id}\n'
        elif node_type == 'subcommand':
            puml += f'usecase "{label}" as {node_id}\n'
        else:
            puml += f'component "{label}" as {node_id}\n'

    # Add edges
    for edge in edges:
        from_node = edge.get('from', '')
        to_node = edge.get('to', '')
        if from_node and to_node:
            puml += f"{from_node} --> {to_node}\n"

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_cmd_cli_lod2(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD2 PlantUML for CMD CLI: detailed argument parsing."""
    cmd_id = data.get('id', 'UNKNOWN')
    title = f"{cmd_id} - {data.get('title', 'Untitled')} (LOD2: CLI Detail)"

    puml = generate_puml_header(title, str(ir_file))

    puml += "note as N1\n"
    puml += "  **LOD2: Argument parsing detail**\n"
    puml += "  \n"
    puml += "  See code layer for implementation details.\n"
    puml += "end note\n"

    # Add basic structure
    nodes = data.get('nodes', [])
    for node in nodes[:10]:  # Limit for readability
        node_id = node['id']
        label = escape_puml(node.get('label', node_id))
        puml += f'component "{label}" as {node_id}\n'

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_cmd_code_lod0(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD0 PlantUML for CMD code: high-level modules."""
    cmd_id = data.get('id', 'UNKNOWN')
    title = f"{cmd_id} - {data.get('title', 'Untitled')} (LOD0: Code Modules)"

    puml = generate_puml_header(title, str(ir_file))

    calls = data.get('calls', [])

    if calls:
        # Extract unique modules
        modules = set()
        for call in calls:
            if '.' in call:
                module = '.'.join(call.split('.')[:-1])
                modules.add(module)

        puml += "package \"Code Modules\" {\n"
        for module in sorted(modules)[:10]:  # Limit to top 10
            module_name = module.split('.')[-1]
            puml += f'  component "{escape_puml(module_name)}" as {module_name}\n'
        puml += "}\n"
    else:
        puml += "note as N1 #FFFFCC\n"
        puml += "  No call graph available\n"
        puml += "end note\n"

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_cmd_code_lod1(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD1 PlantUML for CMD code: key functions."""
    cmd_id = data.get('id', 'UNKNOWN')
    title = f"{cmd_id} - {data.get('title', 'Untitled')} (LOD1: Code Functions)"

    puml = generate_puml_header(title, str(ir_file))

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    calls = data.get('calls', [])

    if not calls and not nodes:
        puml += "note as N1 #FFFFCC\n"
        puml += "  **Call graph not yet expanded**\n"
        puml += "  \n"
        puml += "  This will be populated from code analysis.\n"
        puml += "end note\n"
    else:
        # Add function nodes
        function_nodes = [n for n in nodes if n.get('type') in ['function', 'method']]
        for node in function_nodes[:15]:  # Limit to top 15
            node_id = node['id']
            label = escape_puml(node.get('label', node_id))
            module = node.get('module', '')
            if module:
                puml += f'rectangle "{label}\\n({module})" as {node_id}\n'
            else:
                puml += f'rectangle "{label}" as {node_id}\n'

        # Add call edges
        for edge in edges[:20]:  # Limit edges
            from_node = edge.get('from', '')
            to_node = edge.get('to', '')
            edge_type = edge.get('type', 'call')
            if from_node and to_node and edge_type == 'call':
                puml += f"{from_node} --> {to_node}\n"

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_cmd_code_lod2(data: Dict[str, Any], ir_file: Path) -> str:
    """Generate LOD2 PlantUML for CMD code: detailed callchain."""
    cmd_id = data.get('id', 'UNKNOWN')
    title = f"{cmd_id} - {data.get('title', 'Untitled')} (LOD2: Code Detail)"

    puml = generate_puml_header(title, str(ir_file))

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    calls = data.get('calls', [])

    if not calls:
        puml += "note as N1 #FFFFCC\n"
        puml += "  **Detailed call graph not yet expanded**\n"
        puml += "  \n"
        puml += "  This will show:\n"
        puml += "  * Full function call chains\n"
        puml += "  * Data flow through functions\n"
        puml += "  * Store interactions\n"
        puml += "end note\n"
    else:
        # Show all nodes in detail
        for node in nodes:
            node_id = node['id']
            node_type = node.get('type', 'unknown')
            label = escape_puml(node.get('label', node_id))
            module = node.get('module', '')

            if node_type == 'function':
                puml += f'rectangle "{label}\\n{module}" as {node_id} #E6F3FF\n'
            elif node_type == 'datastore':
                puml += f'database "{label}" as {node_id} #FFE6E6\n'
            elif node_type == 'actor':
                puml += f'actor "{label}" as {node_id}\n'
            else:
                puml += f'component "{label}" as {node_id}\n'

        # Show all edges
        for edge in edges:
            from_node = edge.get('from', '')
            to_node = edge.get('to', '')
            edge_type = edge.get('type', 'call')

            if from_node and to_node:
                if edge_type == 'call':
                    puml += f"{from_node} --> {to_node}\n"
                elif edge_type == 'data':
                    puml += f"{from_node} ..> {to_node} : data\n"
                else:
                    puml += f"{from_node} --> {to_node}\n"

    puml += add_evidence_note(data)
    puml += add_ledger_note(data)

    puml += generate_puml_footer()
    return puml


def generate_all_layers(data: Dict[str, Any], ir_file: Path,
                        lod: int, is_wf: bool, layer: str = None) -> str:
    """Generate combined all_layers diagram."""
    if is_wf:
        wf_id = data.get('wf_id', 'UNKNOWN')
        title = f"{wf_id} - Combined Layers (LOD{lod})"
    else:
        cmd_id = data.get('id', 'UNKNOWN')
        title = f"{cmd_id} - Combined Layers (LOD{lod})"

    puml = generate_puml_header(title, str(ir_file))

    puml += "note as N1\n"
    puml += f"  **Combined view (LOD{lod})**\n"
    puml += "  \n"
    puml += "  This diagram combines:\n"
    if is_wf:
        puml += "  * Intent layer (workflow logic)\n"
        puml += "  * Command integration\n"
    else:
        puml += "  * CLI layer (command surface)\n"
        puml += "  * Code layer (implementation)\n"
    puml += "end note\n"

    # Add a representative structure
    if is_wf:
        if lod == 0:
            puml += generate_wf_lod0(data, ir_file).split('@startuml')[1].split('@enduml')[0]
        elif lod == 1:
            puml += generate_wf_lod1(data, ir_file).split('@startuml')[1].split('@enduml')[0]
        else:
            puml += generate_wf_lod2(data, ir_file).split('@startuml')[1].split('@enduml')[0]
    else:
        # For CMD, we need to load both cli and code layers
        if lod == 0:
            puml += "' CLI + Code LOD0 combined view\n"
        elif lod == 1:
            puml += "' CLI + Code LOD1 combined view\n"
        else:
            puml += "' CLI + Code LOD2 combined view\n"

    puml += generate_puml_footer()
    return puml


def process_wf_file(wf_file: Path):
    """Process a single WF intent file and generate all LOD variants."""
    print(f"Processing WF: {wf_file.name}")

    data = load_yaml(wf_file)
    wf_id = data.get('wf_id', wf_file.stem)

    # Generate LOD0, LOD1, LOD2
    variants = [
        ('intent.lod0', generate_wf_lod0(data, wf_file)),
        ('intent.lod1', generate_wf_lod1(data, wf_file)),
        ('intent.lod2', generate_wf_lod2(data, wf_file)),
        ('all_layers.lod0', generate_all_layers(data, wf_file, 0, True)),
        ('all_layers.lod1', generate_all_layers(data, wf_file, 1, True)),
        ('all_layers.lod2', generate_all_layers(data, wf_file, 2, True)),
    ]

    for variant_name, puml_content in variants:
        out_file = PUML_OUT_DIR / f"{wf_id}.{variant_name}.puml"
        with open(out_file, 'w') as f:
            f.write(puml_content)
        print(f"  Generated: {out_file.name}")


def process_cmd_file(cmd_file: Path):
    """Process a single CMD IR file and generate all LOD variants."""
    print(f"Processing CMD: {cmd_file.name}")

    data = load_yaml(cmd_file)
    cmd_id = data.get('id', cmd_file.stem.split('.')[0])
    layer = data.get('layer', 'unknown')

    if layer == 'cli':
        variants = [
            ('cli.lod0', generate_cmd_cli_lod0(data, cmd_file)),
            ('cli.lod1', generate_cmd_cli_lod1(data, cmd_file)),
            ('cli.lod2', generate_cmd_cli_lod2(data, cmd_file)),
        ]
    elif layer == 'code':
        variants = [
            ('code.lod0', generate_cmd_code_lod0(data, cmd_file)),
            ('code.lod1', generate_cmd_code_lod1(data, cmd_file)),
            ('code.lod2', generate_cmd_code_lod2(data, cmd_file)),
        ]
    else:
        print(f"  WARNING: Unknown layer '{layer}', skipping")
        return

    for variant_name, puml_content in variants:
        out_file = PUML_OUT_DIR / f"{cmd_id}.{variant_name}.puml"
        with open(out_file, 'w') as f:
            f.write(puml_content)
        print(f"  Generated: {out_file.name}")


def generate_cmd_all_layers():
    """Generate all_layers combined diagrams for each CMD."""
    print("\nGenerating CMD all_layers diagrams...")

    # Find all unique CMD IDs
    cmd_files = list(CMD_IR_DIR.glob("CMD-*.yaml"))
    cmd_ids = set()
    for f in cmd_files:
        cmd_id = f.stem.split('.')[0]
        cmd_ids.add(cmd_id)

    for cmd_id in sorted(cmd_ids):
        cli_file = CMD_IR_DIR / f"{cmd_id}.cli.yaml"
        code_file = CMD_IR_DIR / f"{cmd_id}.code.yaml"

        if not cli_file.exists() or not code_file.exists():
            print(f"  Skipping {cmd_id}: missing cli or code layer")
            continue

        cli_data = load_yaml(cli_file)
        code_data = load_yaml(code_file)

        # Generate combined diagrams at each LOD
        for lod in [0, 1, 2]:
            out_file = PUML_OUT_DIR / f"{cmd_id}.all_layers.lod{lod}.puml"

            title = f"{cmd_id} - Combined CLI+Code (LOD{lod})"
            puml = generate_puml_header(title, str(cli_file))

            puml += f"note as N1\n"
            puml += f"  **Combined CLI + Code view (LOD{lod})**\n"
            puml += "end note\n"

            # Simplified combined view
            puml += "\npackage \"CLI Layer\" #E6F3FF {\n"
            for cmd in cli_data.get('commands', [])[:5]:
                puml += f'  usecase "{escape_puml(cmd)}"\n'
            puml += "}\n"

            puml += "\npackage \"Code Layer\" #FFE6E6 {\n"
            for call in code_data.get('calls', [])[:5]:
                func_name = call.split('.')[-1]
                puml += f'  rectangle "{escape_puml(func_name)}"\n'
            puml += "}\n"

            puml += add_evidence_note(cli_data)
            puml += add_ledger_note(code_data)
            puml += generate_puml_footer()

            with open(out_file, 'w') as f:
                f.write(puml)
            print(f"  Generated: {out_file.name}")


def render_svg():
    """Render all PlantUML files to SVG."""
    print("\nRendering PlantUML to SVG...")

    puml_files = list(PUML_OUT_DIR.glob("*.puml"))
    if not puml_files:
        print("  No PlantUML files found!")
        return False

    try:
        cmd = [PLANTUML_CMD, "-tsvg", "-o", str(SVG_OUT_DIR)] + [str(f) for f in puml_files]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  ERROR: PlantUML failed:\n{result.stderr}")
            return False

        svg_count = len(list(SVG_OUT_DIR.glob("*.svg")))
        print(f"  ✓ Rendered {svg_count} SVG files")
        return True

    except FileNotFoundError:
        print(f"  ERROR: PlantUML not found at {PLANTUML_CMD}")
        return False


def generate_index():
    """Generate browse index with links to all diagrams."""
    print("\nGenerating index.md...")

    wf_files = sorted(WF_IR_DIR.glob("WF-*.intent.yaml"))
    cmd_ids = set()
    for f in CMD_IR_DIR.glob("CMD-*.yaml"):
        cmd_ids.add(f.stem.split('.')[0])

    lines = ["# Maestro v2 Workflow Diagrams", ""]
    lines.append("Generated from YAML IR with LOD0/LOD1/LOD2 variants.")
    lines.append("")

    # Workflow diagrams
    lines.append("## Workflow Diagrams")
    lines.append("")

    for wf_file in wf_files:
        data = load_yaml(wf_file)
        wf_id = data.get('wf_id', wf_file.stem)
        title = data.get('title', 'Untitled')

        lines.append(f"### {wf_id} - {title}")
        lines.append("")

        lines.append("**Intent Layer:**")
        lines.append(f"- [LOD0 (Spine)](svg/{wf_id}.intent.lod0.svg) | "
                    f"[PUML](puml/{wf_id}.intent.lod0.puml)")
        lines.append(f"- [LOD1 (Workflow)](svg/{wf_id}.intent.lod1.svg) | "
                    f"[PUML](puml/{wf_id}.intent.lod1.puml)")
        lines.append(f"- [LOD2 (Code)](svg/{wf_id}.intent.lod2.svg) | "
                    f"[PUML](puml/{wf_id}.intent.lod2.puml)")
        lines.append("")

        lines.append("**All Layers:**")
        lines.append(f"- [LOD0](svg/{wf_id}.all_layers.lod0.svg) | "
                    f"[LOD1](svg/{wf_id}.all_layers.lod1.svg) | "
                    f"[LOD2](svg/{wf_id}.all_layers.lod2.svg)")
        lines.append("")

    # Command diagrams
    lines.append("## Command Diagrams")
    lines.append("")

    for cmd_id in sorted(cmd_ids):
        lines.append(f"### {cmd_id}")
        lines.append("")

        cli_file = CMD_IR_DIR / f"{cmd_id}.cli.yaml"
        code_file = CMD_IR_DIR / f"{cmd_id}.code.yaml"

        if cli_file.exists():
            lines.append("**CLI Layer:**")
            lines.append(f"- [LOD0](svg/{cmd_id}.cli.lod0.svg) | "
                        f"[LOD1](svg/{cmd_id}.cli.lod1.svg) | "
                        f"[LOD2](svg/{cmd_id}.cli.lod2.svg)")
            lines.append("")

        if code_file.exists():
            lines.append("**Code Layer:**")
            lines.append(f"- [LOD0](svg/{cmd_id}.code.lod0.svg) | "
                        f"[LOD1](svg/{cmd_id}.code.lod1.svg) | "
                        f"[LOD2](svg/{cmd_id}.code.lod2.svg)")
            lines.append("")

        if cli_file.exists() and code_file.exists():
            lines.append("**All Layers:**")
            lines.append(f"- [LOD0](svg/{cmd_id}.all_layers.lod0.svg) | "
                        f"[LOD1](svg/{cmd_id}.all_layers.lod1.svg) | "
                        f"[LOD2](svg/{cmd_id}.all_layers.lod2.svg)")
            lines.append("")

    # Write index
    with open(INDEX_OUT, 'w') as f:
        f.write('\n'.join(lines))

    print(f"  ✓ Generated {INDEX_OUT}")


def main():
    """Main entry point."""
    print("Maestro v2 Generator: YAML IR → PlantUML → SVG")
    print("=" * 60)

    # Create output directories
    PUML_OUT_DIR.mkdir(parents=True, exist_ok=True)
    SVG_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process WF files
    print("\n1. Processing WF intent files...")
    wf_files = sorted(WF_IR_DIR.glob("WF-*.intent.yaml"))
    print(f"Found {len(wf_files)} WF files")

    for wf_file in wf_files:
        process_wf_file(wf_file)

    # Process CMD files
    print("\n2. Processing CMD IR files...")
    cmd_files = sorted(CMD_IR_DIR.glob("CMD-*.yaml"))
    print(f"Found {len(cmd_files)} CMD files")

    for cmd_file in cmd_files:
        process_cmd_file(cmd_file)

    # Generate CMD all_layers
    generate_cmd_all_layers()

    # Render SVG
    print("\n3. Rendering SVG files...")
    if not render_svg():
        print("WARNING: SVG rendering failed, but PlantUML files are ready")

    # Generate index
    print("\n4. Generating index...")
    generate_index()

    print("\n" + "=" * 60)
    print("✓ Generation complete!")
    print(f"  PlantUML files: {PUML_OUT_DIR}")
    print(f"  SVG files: {SVG_OUT_DIR}")
    print(f"  Index: {INDEX_OUT}")


if __name__ == '__main__':
    main()
