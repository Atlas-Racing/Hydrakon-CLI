import typer
import sys
import os
from rich.console import Console

app = typer.Typer(help="Run specific tests.")
console = Console()

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
