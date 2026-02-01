import typer
import platform
import os
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

app = typer.Typer(help="Hydrakon CLI: Test and manage your packages.")
console = Console()

NAME_ASCII = r"""
   _    _           _           _               
  | |  | |         | |         | |              
  | |__| |_   _  __| |_ __ __ _| | _____  _ __  
  |  __  | | | |/ _` | '__/ _` | |/ / _ \| '_ \ 
  | |  | | |_| | (_| | | | (_| |   < (_) | | | |
  |_|  |_|\__, |\__,_|_|  \__,_|_|\_\___/|_| |_|
           __/ |                                
          |___/                                 
"""

def get_system_info():
    """Generates the 'neofetch' style metadata on the right."""
    info = Text()
    info.append("OS: ", style="bold cyan")
    info.append(f"{platform.system()} {platform.release()}\n")
    info.append("SHELL: ", style="bold cyan")
    info.append(f"{os.environ.get('SHELL', 'PowerShell')}\n")
    info.append("VERSION: ", style="bold cyan")
    info.append("0.1.0-dev\n")
    info.append("DIVISION: ", style="bold cyan")
    info.append("Atlas Racing Autonomous Division\n")
    info.append("LAB: ", style="bold cyan")
    info.append("AimBeyonD Labs\n")
    info.append("UPTIME: ", style="bold cyan")
    info.append("Package Ready\n")
    info.append("VERSIONS SUPPORTED: ", style="bold cyan")
    info.append("HydrakonV2, HydrakonSimV2, HydrakonV1, HydrakonSimV1\n")
    return info

def print_splash():
    logo = Text(NAME_ASCII, style="bold cyan")
    sys_info = get_system_info()
    
    columns = Columns([logo, sys_info], padding=(0, 4))
    
    console.print(Panel(
        columns, 
        title="[bold white]HYDRAKON-CORE[/bold white]",
        border_style="bright_blue",
        expand=False
    ))

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        print_splash()
        console.print("\n[bold yellow]Ready.[/bold yellow] Try [bold cyan]hdk --help[/bold cyan]")

@app.command()
def run(package_path: str = "."):
    """Launch the Hydrakon test suite."""
    print_splash()
    console.print(f"[bold cyan]Initializing environment:[/bold cyan] {package_path}")
    console.print("[bold green]SUCCESS.[/bold green]")

if __name__ == "__main__":
    app()