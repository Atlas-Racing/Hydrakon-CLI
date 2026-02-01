import typer
import subprocess
import time
import re
import yaml
from pathlib import Path
from collections import defaultdict
from rich.console import Console
from rich.tree import Tree
import shutil

app = typer.Typer(help="Visualize system states.")
console = Console()

def run_capture(topic: str, duration: float = 2.0) -> str:
    """Captures topic output for a specific duration."""
    cmd = ["ros2", "topic", "echo", topic, "--no-arr"]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        time.sleep(duration)
        proc.terminate()
        try:
            outs, errs = proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            outs, errs = proc.communicate()
        return outs
    except FileNotFoundError:
        return ""
    except Exception as e:
        return ""

def parse_transforms(raw_data: str) -> list[tuple[str, str]]:
    """
    Parses `ros2 topic echo` output to extract (parent, child) tuples.
    """
    connections = []
    messages = raw_data.split("---")
    
    for msg in messages:
        lines = msg.splitlines()
        current_parent = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("frame_id:"):
                current_parent = line.split(":", 1)[1].strip().replace("'", "").replace('"', "")
            elif line.startswith("child_frame_id:"):
                if current_parent:
                    child = line.split(":", 1)[1].strip().replace("'", "").replace('"', "")
                    connections.append((current_parent, child))
                    current_parent = None 
                    
    return connections

def build_ascii_tree(connections: list[tuple[str, str]], filter_nodes: set[str] = None):
    if not connections:
        console.print("[yellow]No TF data found.[/yellow]")
        return

    # Build adjacency list
    children_map = defaultdict(set)
    all_nodes = set()
    children_nodes = set()
    
    for parent, child in connections:
        children_map[parent].add(child)
        all_nodes.add(parent)
        all_nodes.add(child)
        children_nodes.add(child)
    
    roots = all_nodes - children_nodes
    
    if not roots:
        if all_nodes:
            roots = {next(iter(all_nodes))}
        else:
            console.print("[red]Could not determine TF tree structure.[/red]")
            return

    def process_node(node_name, tree_node=None):
        """
        :param node_name: Current node to process
        :param tree_node: The Rich Tree node to append to. If None, we are looking for a root.
        """
        is_visible = (filter_nodes is None) or (node_name in filter_nodes)
        
        current_tree_node = tree_node

        if is_visible:
            if tree_node is None:
                current_tree_node = Tree(f"[bold cyan]{node_name}[/bold cyan]")
            else:
                current_tree_node = tree_node.add(f"[bold green]{node_name}[/bold green]")
        
        child_visual_roots = []
        if node_name in children_map:
            for child in sorted(children_map[node_name]):
                result = process_node(child, current_tree_node)
                if result:
                    child_visual_roots.append(result)
        
        if tree_node is None and is_visible:
            return current_tree_node
        
        if tree_node is None and not is_visible:
            return child_visual_roots
            
        return None

    visual_roots = []
    
    def collect_roots(res):
        if isinstance(res, Tree):
            visual_roots.append(res)
        elif isinstance(res, list):
            for r in res:
                collect_roots(r)

    for root in sorted(roots):
        res = process_node(root, None)
        collect_roots(res)

    if not visual_roots and filter_nodes is not None:
         console.print("[yellow]No configured frames found in the active TF tree.[/yellow]")

    for t in visual_roots:
        console.print(t)
        console.print("")

@app.command()
def tfs(
    duration: float = typer.Option(2.0, help="Seconds to listen for transforms"),
    config: Path = typer.Option("hydrakon.yaml", help="Path to configuration file"),
    show_all: bool = typer.Option(False, "--all", help="Show all TFs, ignoring config"),
):
    """
    Captures /tf and /tf_static and displays the TF tree in ASCII.
    """
    if not shutil.which("ros2"):
        console.print("[bold red]ERROR:[/bold red] 'ros2' command not found.")
        raise typer.Exit(code=1)
        
    filter_set = None
    if not show_all:
        if config.exists():
            with open(config, "r") as f:
                try:
                    data = yaml.safe_load(f)
                    frames = data.get("frames", [])
                    if frames:
                        filter_set = {item["name"] for item in frames if "name" in item}
                        console.print(f"[cyan]Filtering for {len(filter_set)} configured frames...[/cyan]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not parse config: {e}. Showing all.[/yellow]")
        else:
            console.print(f"[yellow]Config '{config}' not found. Showing all.[/yellow]")

    console.print(f"[cyan]Listening for transforms for {duration} seconds...[/cyan]")
    
    static_data = run_capture("/tf_static", duration=1.0)
    dynamic_data = run_capture("/tf", duration=duration)
    
    connections = []
    connections.extend(parse_transforms(static_data))
    connections.extend(parse_transforms(dynamic_data))
    
    unique_connections = list(set(connections))
    
    console.print(f"[green]Found {len(unique_connections)} connections.[/green]")
    
    build_ascii_tree(unique_connections, filter_nodes=filter_set)
