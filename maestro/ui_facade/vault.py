"""
UI Facade for Vault Operations

This module provides structured data access to logs and artifacts across all subsystems.
It acts as a unified interface to locate, retrieve, and export logs and artifacts.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Literal
import os
import json
import shutil
from datetime import datetime
import zipfile
import tarfile
from pathlib import Path


SourceType = Literal["logs", "artifacts", "diffs", "snapshots", "summaries", "human_judgment"]
SubsystemType = Literal["plan", "task", "build", "convert", "arbitration", "replay", "refactor", "tui"]
ItemType = Literal["log", "artifact", "diff", "snapshot", "summary", "json", "text", "other"]


@dataclass
class VaultItem:
    """Represents a single item in the vault (log, artifact, diff, etc.)"""
    id: str
    source_type: SourceType
    subtype: ItemType
    timestamp: str
    origin: str  # e.g., task_id, run_id, stage
    description: str
    path: str
    size: int
    subsystem: SubsystemType
    related_entities: List[Dict[str, str]]  # Related items like task_id, run_id, plan_id


@dataclass
class VaultFilter:
    """Filter criteria for listing vault items"""
    source_types: Optional[List[SourceType]] = None
    subsystems: Optional[List[SubsystemType]] = None
    time_range: Literal["recent", "all"] = "all"
    search_text: Optional[str] = None
    origin_filter: Optional[str] = None


@dataclass
class VaultMetadata:
    """Metadata for a vault item"""
    path: str
    size: int
    created_at: str
    modified_at: str
    related_entities: List[Dict[str, str]]
    content_type: str


# Common locations where vault items might be found
VAULT_LOCATIONS = [
    "./.maestro/sessions/",
    "./.maestro/logs/",
    "./.maestro/build_artifacts/",
    "./.maestro/diffs/",
    "./.maestro/snapshots/",
    "./outputs/",
    "./.maestro/arbitration/",
    "./.maestro/convert/",
    "./.maestro/refactor/",
    "./.maestro/replay/",
    "./.maestro/plan/"
]


def _find_vault_files(locations: List[str], filter_extensions: Optional[List[str]] = None) -> List[str]:
    """Find all potential vault files in specified locations."""
    files = []
    
    for location in locations:
        if not os.path.exists(location):
            continue
        
        for root, dirs, filenames in os.walk(location):
            for filename in filenames:
                if filter_extensions:
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext not in filter_extensions:
                        continue
                
                filepath = os.path.join(root, filename)
                
                # Skip temporary and hidden files
                if not filename.startswith('.') and not any(part.startswith('.') for part in Path(filepath).parts):
                    files.append(filepath)
    
    return files


def _classify_file(filepath: str) -> tuple[SourceType, ItemType, SubsystemType]:
    """Classify a file based on its path to determine source type, item type and subsystem."""
    path_lower = filepath.lower()

    # Determine source type based on path
    source_type: SourceType = "artifacts"  # default

    if "log" in path_lower:
        source_type = "logs"
    elif "diff" in path_lower:
        source_type = "diffs"
    elif "snapshot" in path_lower:
        source_type = "snapshots"
    elif "summary" in path_lower:
        source_type = "summaries"
    elif "human_judgment" in path_lower or "human_judgment" in path_lower or "evidence" in path_lower:
        source_type = "human_judgment"

    # Determine item type based on extension
    _, ext = os.path.splitext(filepath.lower())
    item_type: ItemType = "other"

    if ext in ['.log', '.txt', '.out']:
        item_type = "log"
    elif ext in ['.json']:
        item_type = "json"
    elif ext in ['.diff', '.patch']:
        item_type = "diff"
    elif ext in ['.txt', '.md', '.rst', '.csv', '.xml']:
        item_type = "text"
    else:
        item_type = "artifact"

    # Determine subsystem based on path
    subsystem: SubsystemType = "tui"  # default

    if "plan" in path_lower:
        subsystem = "plan"
    elif "task" in path_lower or "subtask" in path_lower:
        subsystem = "task"
    elif "build" in path_lower:
        subsystem = "build"
    elif "convert" in path_lower:
        subsystem = "convert"
    elif "arbitration" in path_lower:
        subsystem = "arbitration"
    elif "replay" in path_lower:
        subsystem = "replay"
    elif "refactor" in path_lower:
        subsystem = "refactor"

    return source_type, item_type, subsystem


def _extract_origin_and_description(filepath: str) -> tuple[str, str]:
    """Extract origin (task_id, run_id, etc.) and description from filepath."""
    path_parts = Path(filepath).parts
    
    # Look for common identifiers in the path
    origin = "unknown"
    description = os.path.basename(filepath)
    
    for part in reversed(path_parts):
        if len(part) >= 8 and '-' in part and all(c.isalnum() or c in '-_' for c in part):
            # Likely a UUID or identifier
            origin = part
            break
    
    # Try to extract more meaningful description
    parent_dir = os.path.dirname(filepath)
    grandparent_dir = os.path.dirname(parent_dir)
    
    if "task" in parent_dir.lower() or "subtask" in parent_dir.lower():
        origin = os.path.basename(parent_dir)  # Use the task directory name as origin
    elif "run" in parent_dir.lower():
        origin = os.path.basename(parent_dir)  # Use the run directory name as origin
    elif "plan" in parent_dir.lower():
        origin = os.path.basename(parent_dir)  # Use the plan directory name as origin
    
    return origin, description


def _get_related_entities(filepath: str) -> List[Dict[str, str]]:
    """Extract potential related entities from the filepath."""
    relations = []
    
    # Extract potential IDs from the path
    for part in Path(filepath).parts:
        if len(part) >= 8 and ('-' in part or '_' in part) and any(c.isalnum() for c in part):
            # Might be a UUID or ID-like string
            if any(keyword in part.lower() for keyword in ['task', 'run', 'plan']):
                entity_type = 'task' if 'task' in part.lower() else \
                             'run' if 'run' in part.lower() else \
                             'plan' if 'plan' in part.lower() else 'unknown'
                relations.append({"type": entity_type, "id": part})
            elif len(part) >= 32 and all(c in '0123456789abcdefABCDEF-' for c in part.replace('-', '')):
                # Looks like a UUID
                relations.append({"type": "generic", "id": part})
    
    return relations


def _get_file_timestamp(filepath: str) -> str:
    """Get the creation/modification timestamp of a file."""
    try:
        stat_result = os.stat(filepath)
        # Use the newer of created or modified timestamp
        timestamp = max(stat_result.st_ctime, stat_result.st_mtime)
        return datetime.fromtimestamp(timestamp).isoformat()
    except OSError:
        return datetime.now().isoformat()


def list_items(filters: Optional[VaultFilter] = None) -> List[VaultItem]:
    """
    List all vault items based on filters.
    
    Args:
        filters: Optional filtering criteria
        
    Returns:
        List of vault items matching the criteria
    """
    if filters is None:
        filters = VaultFilter()
    
    all_files = _find_vault_files(VAULT_LOCATIONS)
    items = []
    
    for filepath in all_files:
        source_type, item_type, subsystem = _classify_file(filepath)
        
        # Apply source type filter
        if filters.source_types and source_type not in filters.source_types:
            continue
            
        # Apply subsystem filter  
        if filters.subsystems and subsystem not in filters.subsystems:
            continue
            
        # Apply origin filter
        origin, description = _extract_origin_and_description(filepath)
        if filters.origin_filter and filters.origin_filter.lower() not in origin.lower():
            continue
            
        # Apply search text filter to description and path
        if filters.search_text:
            search_text = filters.search_text.lower()
            if search_text not in description.lower() and search_text not in filepath.lower():
                continue
                
        # Apply time range filter
        timestamp = _get_file_timestamp(filepath)
        if filters.time_range == "recent":
            # Only include items from past week (for example)
            import time
            threshold = datetime.now().timestamp() - (7 * 24 * 60 * 60)  # 7 days ago
            file_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
            if file_time < threshold:
                continue
        
        try:
            size = os.path.getsize(filepath)
            
            related_entities = _get_related_entities(filepath)
            
            item_id = f"{source_type}-{hash(filepath) % 1000000}"
            
            items.append(VaultItem(
                id=item_id,
                source_type=source_type,
                subtype=item_type,
                timestamp=timestamp,
                origin=origin,
                description=description,
                path=filepath,
                size=size,
                subsystem=subsystem,
                related_entities=related_entities
            ))
        except OSError:
            # Skip files that can't be accessed
            continue
    
    # Sort by timestamp (newest first)
    items.sort(key=lambda x: x.timestamp, reverse=True)
    
    return items


def get_item(item_id: str) -> Optional[VaultItem]:
    """
    Get details for a specific vault item by ID.
    
    Args:
        item_id: Unique identifier for the item
        
    Returns:
        Vault item details or None if not found
    """
    # For simplicity, we'll reconstruct the item by listing all and filtering
    # In a production system, we would have a more efficient lookup mechanism
    all_items = list_items()
    for item in all_items:
        if item.id == item_id:
            return item
    return None


def get_item_content(item_id: str) -> str:
    """
    Get the content of a specific vault item.
    
    Args:
        item_id: Unique identifier for the item
        
    Returns:
        Content of the item as string
    """
    item = get_item(item_id)
    if not item:
        raise ValueError(f"Item with ID '{item_id}' not found")
    
    try:
        with open(item.path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except UnicodeDecodeError:
        # If it's a binary file, return hex representation or info
        with open(item.path, 'rb') as f:
            content = f.read()
            return f"<Binary file: {len(content)} bytes>"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def get_item_metadata(item_id: str) -> Optional[VaultMetadata]:
    """
    Get metadata for a specific vault item.
    
    Args:
        item_id: Unique identifier for the item
        
    Returns:
        Metadata for the item or None if not found
    """
    item = get_item(item_id)
    if not item:
        return None
    
    if os.path.exists(item.path):
        stat_result = os.stat(item.path)
        created_at = datetime.fromtimestamp(stat_result.st_ctime).isoformat()
        modified_at = datetime.fromtimestamp(stat_result.st_mtime).isoformat()
        
        # Determine content type based on file extension
        _, ext = os.path.splitext(item.path.lower())
        content_type = ext[1:] if ext else "unknown"
        
        return VaultMetadata(
            path=item.path,
            size=item.size,
            created_at=created_at,
            modified_at=modified_at,
            related_entities=item.related_entities,
            content_type=content_type
        )
    
    return None


def find_related(item_id: str) -> List[VaultItem]:
    """
    Find items related to a specific vault item.

    Args:
        item_id: Unique identifier for the item

    Returns:
        List of related vault items
    """
    item = get_item(item_id)
    if not item:
        return []

    # Find items that share similar origins or paths
    related_items = []
    all_items = list_items()

    for candidate in all_items:
        if candidate.id == item_id:
            continue  # Skip the item itself

        # Check if they share any related entities
        for rel_entity in item.related_entities:
            for cand_entity in candidate.related_entities:
                if rel_entity == cand_entity:
                    related_items.append(candidate)
                    break
            else:
                continue
            break
        else:
            # Check if they share similar origin/parts of path
            if item.origin in candidate.path or candidate.origin in item.path:
                related_items.append(candidate)
            elif os.path.dirname(item.path) == os.path.dirname(candidate.path):
                # Same directory indicates potential relationship
                related_items.append(candidate)

    return related_items


def get_correlation_map(item_id: str) -> Dict[str, List[str]]:
    """
    Get a detailed correlation map for an item showing what other entities it relates to.

    Args:
        item_id: Unique identifier for the item

    Returns:
        Dictionary mapping entity types to their IDs that are related to this item
    """
    item = get_item(item_id)
    if not item:
        return {}

    correlation_map = {
        'tasks': [],
        'plans': [],
        'runs': [],
        'checkpoints': [],
        'arbitration_decisions': []
    }

    # Extract related entities by type
    for entity in item.related_entities:
        entity_type = entity.get('type', 'unknown')
        entity_id = entity.get('id', '')

        if entity_type == 'task':
            correlation_map['tasks'].append(entity_id)
        elif entity_type == 'plan':
            correlation_map['plans'].append(entity_id)
        elif entity_type == 'run':
            correlation_map['runs'].append(entity_id)
        elif 'checkpoint' in entity_type:
            correlation_map['checkpoints'].append(entity_id)
        elif 'arbitration' in entity_type or 'decision' in entity_type:
            correlation_map['arbitration_decisions'].append(entity_id)
        else:
            # For other types, add to an 'other' category
            if 'other' not in correlation_map:
                correlation_map['other'] = []
            correlation_map['other'].append(f"{entity_type}:{entity_id}")

    return correlation_map


def export_items(item_ids: List[str], output_format: Literal["zip", "tar.gz"] = "zip",
                 output_path: Optional[str] = None) -> str:
    """
    Export specified vault items to an archive.

    Args:
        item_ids: List of item IDs to export
        output_format: Format of the export ("zip" or "tar.gz")
        output_path: Optional path for the output file (otherwise auto-generated)

    Returns:
        Path to the created archive
    """
    if not item_ids:
        raise ValueError("No item IDs provided for export")

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".zip" if output_format == "zip" else ".tar.gz"
        output_path = f"./.maestro/vault_export_{timestamp}{ext}"

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create manifest with exported item details
    manifest = {
        "export_time": datetime.now().isoformat(),
        "export_format": output_format,
        "items": []
    }

    # Collect actual item paths and create a mapping for archive structure
    items_to_export = []
    for item_id in item_ids:
        item = get_item(item_id)
        if item and os.path.exists(item.path):
            items_to_export.append(item)
            manifest["items"].append({
                "id": item.id,
                "source_type": item.source_type,
                "subtype": item.subtype,
                "timestamp": item.timestamp,
                "origin": item.origin,
                "description": item.description,
                "original_path": item.path,
                "size": item.size
            })

    # Create the archive
    if output_format == "zip":
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for item in items_to_export:
                archive_path = os.path.basename(item.path)  # Use just the filename to avoid path conflicts
                archive.write(item.path, archive_path)

            # Add manifest
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    else:  # tar.gz
        with tarfile.open(output_path, 'w:gz') as archive:
            for item in items_to_export:
                archive_path = os.path.basename(item.path)  # Use just the filename to avoid path conflicts
                archive.add(item.path, arcname=archive_path)

            # Add manifest by first writing it to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_manifest:
                json.dump(manifest, temp_manifest, indent=2)
                temp_manifest_path = temp_manifest.name

            archive.add(temp_manifest_path, arcname="manifest.json")
            os.unlink(temp_manifest_path)  # Clean up temp file

    return output_path


def export_filtered(filters: Optional[VaultFilter] = None, output_format: Literal["zip", "tar.gz"] = "zip",
                   output_path: Optional[str] = None) -> str:
    """
    Export vault items matching the given filters to an archive.

    Args:
        filters: Optional filtering criteria to determine what to export
        output_format: Format of the export ("zip" or "tar.gz")
        output_path: Optional path for the output file (otherwise auto-generated)

    Returns:
        Path to the created archive
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".zip" if output_format == "zip" else ".tar.gz"
        output_path = f"./.maestro/vault_export_filtered_{timestamp}{ext}"

    # Get items based on filters
    items_to_export = list_items(filters)

    # Create manifest with exported item details
    manifest = {
        "export_time": datetime.now().isoformat(),
        "export_format": output_format,
        "filters_used": {
            "source_types": filters.source_types if filters else None,
            "subsystems": filters.subsystems if filters else None,
            "time_range": filters.time_range if filters else "all",
            "search_text": filters.search_text if filters else None
        } if filters else {},
        "items": []
    }

    # Prepare items for export
    items_with_paths = []
    for item in items_to_export:
        if os.path.exists(item.path):
            items_with_paths.append(item)
            manifest["items"].append({
                "id": item.id,
                "source_type": item.source_type,
                "subtype": item.subtype,
                "timestamp": item.timestamp,
                "origin": item.origin,
                "description": item.description,
                "original_path": item.path,
                "size": item.size
            })

    # Create the archive
    if output_format == "zip":
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for item in items_with_paths:
                archive_path = os.path.basename(item.path)  # Use just the filename to avoid path conflicts
                archive.write(item.path, archive_path)

            # Add manifest
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    else:  # tar.gz
        with tarfile.open(output_path, 'w:gz') as archive:
            for item in items_with_paths:
                archive_path = os.path.basename(item.path)  # Use just the filename to avoid path conflicts
                archive.add(item.path, arcname=archive_path)

            # Add manifest by first writing it to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_manifest:
                json.dump(manifest, temp_manifest, indent=2)
                temp_manifest_path = temp_manifest.name

            archive.add(temp_manifest_path, arcname="manifest.json")
            os.unlink(temp_manifest_path)  # Clean up temp file

    return output_path


def export_run_related(run_id: str, output_format: Literal["zip", "tar.gz"] = "zip",
                      output_path: Optional[str] = None) -> str:
    """
    Export all items related to a specific run ID.

    Args:
        run_id: Run ID to export related items for
        output_format: Format of the export ("zip" or "tar.gz")
        output_path: Optional path for the output file (otherwise auto-generated)

    Returns:
        Path to the created archive
    """
    # Find all items related to this run by searching related_entities
    all_items = list_items()
    run_related_items = []

    for item in all_items:
        for entity in item.related_entities:
            if entity.get('id', '') == run_id or run_id in entity.get('id', ''):
                run_related_items.append(item.id)
                break

    return export_items(run_related_items, output_format, output_path)


def search_items(search_text: str, source_types: Optional[List[SourceType]] = None) -> List[VaultItem]:
    """
    Search for vault items containing the specified text.

    Args:
        search_text: Text to search for
        source_types: Optional list of source types to limit search

    Returns:
        List of matching vault items
    """
    filters = VaultFilter(search_text=search_text, source_types=source_types)
    return list_items(filters)


def store_evidence(vault_item: VaultItem, content: str) -> bool:
    """
    Store evidence content to the vault system.

    Args:
        vault_item: VaultItem metadata for the evidence
        content: Content to store as evidence

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directories for evidence storage
        evidence_dir = "./.maestro/convert/semantic_evidence"
        os.makedirs(evidence_dir, exist_ok=True)

        # Create a file path based on the item ID
        file_path = os.path.join(evidence_dir, f"{vault_item.id}.txt")

        # Write the content to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update the vault item path to reflect the actual storage location
        vault_item.path = file_path

        return True
    except Exception:
        return False


def get_available_subsystems() -> List[SubsystemType]:
    """Get list of all available subsystems."""
    return ["plan", "task", "build", "convert", "arbitration", "replay", "refactor", "tui"]


def get_available_source_types() -> List[SourceType]:
    """Get list of all available source types."""
    return ["logs", "artifacts", "diffs", "snapshots", "summaries"]