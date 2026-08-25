Write-Host "This script outlines the steps to produce an MSI using WiX Toolset. Adapt paths as needed."

# 1. Build the desktop project for release and produce a publish folder
dotnet publish desktop/Jarvis.Desktop/Jarvis.Desktop.csproj -c Release -r win-x64 -p:PublishSingleFile=false -o publish\jarvis

# 2. Prepare backend payload (ensure you have a portable python distribution or venv packaged)
Write-Host "Ensure backend/ contains the python runtime and app code. Place it under publish\jarvis\backend before harvesting."

# 3. Use heat.exe to harvest files into a wxs fragment (requires WiX installed)
# heat dir publish\jarvis -cg AppComponents -dr INSTALLFOLDER -gg -srd -sreg -sfrag -out desktop\installer\Harvested.wxs

# 4. Build the wix installer (example)
# candle desktop\installer\installer.wxs desktop\installer\Harvested.wxs -out desktop\installer\
# light -ext WixUIExtension desktop\installer\installer.wixobj desktop\installer\Harvested.wixobj -out desktop\installer\Jarvis.msi

Write-Host "See desktop/installer/README.md for more guidance."
