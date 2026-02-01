import typer
import sys
import os
import yaml
import subprocess
import shutil
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Run specific tests.")
console = Console()

def run_command(cmd: list[str], timeout: int = 5) -> str:
    """Helper to run shell commands and return stdout."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=True
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except subprocess.CalledProcessError:
        return ""
    except FileNotFoundError:
        return ""

@app.command()
def topics(
    config: Path = typer.Option("hydrakon.yaml", help="Path to configuration file")
):
    """Validate ROS 2 topics (Existence, Type, Hz) defined in hydrakon.yaml."""
    if not config.exists():
        console.print(f"[bold red]ERROR:[/bold red] Config file '{config}' not found.")
        raise typer.Exit(code=1)

    # Check if ros2 is installed
    if not shutil.which("ros2"):
        console.print("[bold red]ERROR:[/bold red] 'ros2' command not found in PATH.")
        raise typer.Exit(code=1)

    with open(config, "r") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            console.print(f"[bold red]ERROR:[/bold red] Invalid YAML: {e}")
            raise typer.Exit(code=1)

    topic_configs = data.get("topics", [])
    if not topic_configs:
        console.print("[yellow]No topics found in configuration.[/yellow]")
        return

    # Get active topics once
    console.print("[cyan]Fetching active ROS 2 topics...[/cyan]")
    active_topics_raw = run_command(["ros2", "topic", "list"])
    active_topics = set(active_topics_raw.splitlines())

    table = Table(title="ROS 2 Topic Validation")
    table.add_column("Topic", style="cyan")
    table.add_column("Check", style="magenta")
    table.add_column("Expected", style="green")
    table.add_column("Actual", style="yellow")
    table.add_column("Status", justify="right")

    success_count = 0
    total_checks = 0

    for item in topic_configs:
        name = item.get("name")
        if not name:
            continue

        # 1. Check Existence
        total_checks += 1
        exists = name in active_topics
        status_exists = "[green]PASS[/green]" if exists else "[red]FAIL[/red]"
        if exists:
            success_count += 1
        
        table.add_row(name, "Existence", "True", str(exists), status_exists)

        if not exists:
            # Skip other checks if topic doesn't exist
            continue

        # 2. Check Type
        if "type" in item:
            total_checks += 1
            expected_type = item["type"]
            info_out = run_command(["ros2", "topic", "info", name])
            actual_type = "Unknown"
            if "Type: " in info_out:
                actual_type = info_out.split("Type: ")[1].split()[0]
            
            type_match = actual_type.strip() == expected_type.strip()
            status_type = "[green]PASS[/green]" if type_match else "[red]FAIL[/red]"
            if type_match: 
                success_count += 1
            
            table.add_row(name, "Type", expected_type, actual_type, status_type)

        # 3. Check Hz
        if "hz" in item:
            total_checks += 1
            target_hz = float(item["hz"])
            tolerance = float(item.get("tolerance", 0.1)) # default 10%
            
            console.print(f"Checking Hz for {name} (approx 2s)...")
            
            hz_out = run_command(["ros2", "topic", "hz", name, "--window", "5"], timeout=10)
            
            actual_hz = 0.0
            match = re.search(r"average rate:\s+([\d\.]+)", hz_out)
            if match:
                actual_hz = float(match.group(1))
            
            min_hz = target_hz * (1 - tolerance)
            max_hz = target_hz * (1 + tolerance)
            
            hz_pass = min_hz <= actual_hz <= max_hz
            status_hz = "[green]PASS[/green]" if hz_pass else "[red]FAIL[/red]"
            if hz_pass:
                success_count += 1
            
            table.add_row(name, "Hz", f"{target_hz} (±{int(tolerance*100)}%)", f"{actual_hz:.2f}", status_hz)

    console.print(table)
    
    if success_count == total_checks:
        console.print(f"\n[bold green]ALL CHECKS PASSED ({success_count}/{total_checks})[/bold green]")
    else:
        console.print(f"\n[bold red]SOME CHECKS FAILED ({total_checks - success_count}/{total_checks})[/bold red]")
        raise typer.Exit(code=1)

@app.command()
def can0():
    """Check if the can0 interface exists and is up."""
    exists = False
    is_up = False
    
    if sys.platform.startswith("linux"):
        if os.path.exists("/sys/class/net/can0"):
            exists = True
            try:
                with open("/sys/class/net/can0/operstate", "r") as f:
                    state = f.read().strip()
                if state == "up":
                    is_up = True
            except OSError:
                pass

    if not exists:
        console.print("[bold red]ERROR:[/bold red] Interface 'can0' not found.")
        raise typer.Exit(code=1)
        
    if not is_up:
        console.print("[bold red]ERROR:[/bold red] Interface 'can0' down.")
        raise typer.Exit(code=1)

    console.print("[bold green]SUCCESS:[/bold green] Interface 'can0' found and UP.")
