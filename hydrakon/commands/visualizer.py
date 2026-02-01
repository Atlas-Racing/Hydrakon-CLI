import typer
import subprocess
import time
import re
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
    Looks for pattern:
      frame_id: parent
      ...
      child_frame_id: child
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

def build_ascii_tree(connections: list[tuple[str, str]]):
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
    
    for root in sorted(roots):
        tree = Tree(f"[bold cyan]{root}[/bold cyan]")
        
        def add_children(node_name, tree_node):
            if node_name in children_map:
                for child in sorted(children_map[node_name]):
                    sub_node = tree_node.add(f"[bold green]{child}[/bold green]")
                    add_children(child, sub_node)
        
        add_children(root, tree)
        console.print(tree)
        console.print("") # spacing

@app.command()
def tfs(
    duration: float = typer.Option(2.0, help="Seconds to listen for transforms"),
):
    """
    Captures /tf and /tf_static and displays the TF tree in ASCII.
    """
    if not shutil.which("ros2"):
        console.print("[bold red]ERROR:[/bold red] 'ros2' command not found.")
        raise typer.Exit(code=1)
        
    console.print(f"[cyan]Listening for transforms for {duration} seconds...[/cyan]")
    
    static_data = run_capture("/tf_static", duration=1.0)

    dynamic_data = run_capture("/tf", duration=duration)
    
    connections = []
    connections.extend(parse_transforms(static_data))
    connections.extend(parse_transforms(dynamic_data))
    
    unique_connections = list(set(connections))
    
    console.print(f"[green]Found {len(unique_connections)} connections.[/green]")
    
    build_ascii_tree(unique_connections)

