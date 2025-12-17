"""
Dependency resolution and build ordering module.

Implements topological sort using Kahn's algorithm for building packages
in dependency order as required in Phase 12.
"""

from typing import List, Dict, Set, Any, Optional
from .package import PackageInfo


def kahn_topological_sort(packages: List[PackageInfo]) -> List[PackageInfo]:
    """
    Perform topological sort using Kahn's algorithm to determine build order.
    
    Args:
        packages: List of PackageInfo objects with dependencies
        
    Returns:
        List of packages in build order (dependencies first)
        
    Raises:
        ValueError: If circular dependencies are detected
    """
    # Create adjacency list representation of dependencies
    graph: Dict[str, Set[str]] = {}
    all_nodes: Set[str] = set()
    
    # Initialize the graph with all packages
    for pkg in packages:
        all_nodes.add(pkg.name)
        graph[pkg.name] = set(pkg.dependencies)
    
    # Calculate in-degrees for all nodes
    in_degree: Dict[str, int] = {node: 0 for node in all_nodes}
    
    # Count in-degrees
    for pkg in packages:
        for dep in pkg.dependencies:
            if dep in in_degree:
                in_degree[dep] += 1
    
    # Find nodes with in-degree 0 (no unmet dependencies)
    queue = [node for node in all_nodes if in_degree[node] == 0]
    result: List[PackageInfo] = []
    
    # Process nodes in topological order
    while queue:
        # Remove a node with in-degree 0
        current_name = queue.pop(0)
        
        # Add the corresponding package to the result
        current_pkg = next((pkg for pkg in packages if pkg.name == current_name), None)
        if current_pkg:
            result.append(current_pkg)
        
        # Process all dependent packages
        for pkg in packages:
            if current_name in pkg.dependencies:
                in_degree[pkg.name] -= 1
                if in_degree[pkg.name] == 0:
                    queue.append(pkg.name)
    
    # Check for circular dependencies
    if len(result) != len(all_nodes):
        # Find the unprocessed nodes (indicating cycle)
        processed_names = {pkg.name for pkg in result}
        unprocessed = all_nodes - processed_names
        
        # Identify the cycle by doing a cycle detection
        cycle = find_dependency_cycle(packages, unprocessed)
        if cycle:
            raise ValueError(f"Circular dependency detected: {' -> '.join(cycle)} -> {cycle[0]}")
        else:
            raise ValueError("Circular dependency detected but could not identify the cycle")
    
    return result


def find_dependency_cycle(packages: List[PackageInfo], unprocessed_nodes: Set[str]) -> List[str]:
    """
    Helper function to find a dependency cycle among unprocessed nodes.
    
    Args:
        packages: List of PackageInfo objects
        unprocessed_nodes: Set of nodes that weren't processed (indicating cycle)
        
    Returns:
        List of package names forming a cycle, or empty list if no cycle found
    """
    # Create dependency graph for unprocessed nodes only
    graph: Dict[str, List[str]] = {}
    for pkg in packages:
        if pkg.name in unprocessed_nodes:
            graph[pkg.name] = [dep for dep in pkg.dependencies if dep in unprocessed_nodes]
    
    # Use DFS to find a cycle
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    parent: Dict[str, str] = {}
    
    def dfs(node: str, path: List[str]) -> Optional[List[str]]:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                parent[neighbor] = node
                cycle = dfs(neighbor, path)
                if cycle:
                    return cycle
            elif neighbor in rec_stack:
                # Found cycle - reconstruct it
                cycle_start_idx = path.index(neighbor)
                cycle_path = path[cycle_start_idx:] + [neighbor]
                return cycle_path
        
        path.pop()
        rec_stack.remove(node)
        return None
    
    for node in unprocessed_nodes:
        if node not in visited:
            cycle = dfs(node, [])
            if cycle:
                return cycle
    
    return []


def resolve_build_order(packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Resolve build order for a list of package dictionaries from repo index.
    
    Args:
        packages: List of package dictionaries from repo index
        
    Returns:
        List of packages in build order (dependencies first)
        
    Raises:
        ValueError: If circular dependencies are detected
    """
    # Convert package dictionaries to PackageInfo objects
    package_info_list = []
    name_to_original = {}  # Map from name to original dict for returning
    
    for pkg_dict in packages:
        pkg_info = PackageInfo(
            name=pkg_dict['name'],
            dir=pkg_dict['dir'],
            upp_path=pkg_dict.get('upp_path', ''),
            files=pkg_dict.get('files', []),
            upp=pkg_dict.get('upp'),
            build_system=pkg_dict.get('build_system', 'upp'),
            dependencies=pkg_dict.get('dependencies', []),
            groups=pkg_dict.get('groups', []),
            ungrouped_files=pkg_dict.get('ungrouped_files', [])
        )
        
        package_info_list.append(pkg_info)
        name_to_original[pkg_info.name] = pkg_dict
    
    # Perform topological sort
    sorted_packages = kahn_topological_sort(package_info_list)
    
    # Convert back to original dictionary format
    result = []
    for pkg_info in sorted_packages:
        original_dict = name_to_original[pkg_info.name]
        result.append(original_dict)
    
    return result


def get_build_dependencies(graph: Dict[str, List[str]], start_package: str) -> List[str]:
    """
    Get all dependencies (direct and transitive) for a package.
    
    Args:
        graph: Dependency graph as dict mapping package name to list of dependencies
        start_package: Package name to get dependencies for
        
    Returns:
        List of all dependencies in no particular order
    """
    dependencies = set()
    visited = set()
    
    def dfs(pkg_name):
        if pkg_name in visited or pkg_name not in graph:
            return
        visited.add(pkg_name)
        
        for dep in graph.get(pkg_name, []):
            if dep not in dependencies:
                dependencies.add(dep)
                dfs(dep)
    
    dfs(start_package)
    return list(dependencies)


def get_build_dependents(graph: Dict[str, List[str]], start_package: str) -> List[str]:
    """
    Get all packages that depend on a given package (direct and transitive).
    
    Args:
        graph: Dependency graph as dict mapping package name to list of dependencies
        start_package: Package name to get dependents for
        
    Returns:
        List of all dependents in no particular order
    """
    dependents = set()
    
    # Build reverse graph (dependents -> dependencies)
    reverse_graph: Dict[str, List[str]] = {}
    for pkg, deps in graph.items():
        for dep in deps:
            if dep not in reverse_graph:
                reverse_graph[dep] = []
            reverse_graph[dep].append(pkg)
    
    visited = set()
    
    def dfs(pkg_name):
        if pkg_name in visited or pkg_name not in reverse_graph:
            return
        visited.add(pkg_name)
        
        for dep_pkg in reverse_graph.get(pkg_name, []):
            if dep_pkg not in dependents:
                dependents.add(dep_pkg)
                dfs(dep_pkg)
    
    dfs(start_package)
    return list(dependents)


def create_dependency_graph(packages: List[PackageInfo]) -> Dict[str, Set[str]]:
    """
    Create a dependency graph from packages.
    
    Args:
        packages: List of PackageInfo objects
        
    Returns:
        Dict mapping package name to set of its dependencies
    """
    graph = {}
    for pkg in packages:
        graph[pkg.name] = set(pkg.dependencies)
    return graph