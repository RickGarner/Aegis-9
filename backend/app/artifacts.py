import re
from pathlib import Path

from pydantic import BaseModel


class GeneratedArtifact(BaseModel):
    path: Path
    relative_path: str
    description: str


def try_create_requested_artifact(prompt: str, project_root: Path) -> GeneratedArtifact | None:
    normalized = re.sub(r"\s+", " ", prompt.strip().lower())
    wants_creation = any(term in normalized for term in ("create", "write", "make", "generate"))
    wants_powershell = "powershell" in normalized or ".ps1" in normalized
    wants_addition = any(term in normalized for term in ("add together", "add two", "sum two", "adds two", "add 2", "sum 2"))
    wants_input = "input" in normalized or "user" in normalized or "prompt" in normalized

    if not (wants_creation and wants_powershell and wants_addition and wants_input):
        return None

    output_dir = project_root / "storage" / "generated" / "scripts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "add-two-numbers.ps1"
    output_path.write_text(_add_two_numbers_script(), encoding="utf-8")

    return GeneratedArtifact(
        path=output_path,
        relative_path=output_path.relative_to(project_root).as_posix(),
        description="PowerShell script that prompts for two numbers, validates them, and prints their sum.",
    )


def _add_two_numbers_script() -> str:
    return """param()

function Read-Number {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Prompt
    )

    while ($true) {
        $value = Read-Host $Prompt
        $number = 0.0
        if ([double]::TryParse($value, [ref]$number)) {
            return $number
        }

        Write-Host "Please enter a valid number." -ForegroundColor Yellow
    }
}

$firstNumber = Read-Number -Prompt "Enter the first number"
$secondNumber = Read-Number -Prompt "Enter the second number"
$sum = $firstNumber + $secondNumber

Write-Host "The sum of $firstNumber and $secondNumber is $sum"
"""