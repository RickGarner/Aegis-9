Installer scaffolding and guidance

This folder contains guidance for producing an MSI or MSIX installer that bundles the WPF application and the Python FastAPI backend.

Recommendation (initial):
- Use WiX Toolset to produce an MSI that places files under Program Files and creates shortcuts.
- Bundle a portable Python distribution or the embeddable Python runtime inside the `backend/` folder.
- The installer should include the `backend/` folder next to the installed `Jarvis.Desktop.exe` so the app can launch it from `AppDomain.CurrentDomain.BaseDirectory + "backend"`.

Minimum installer payload layout (installed directory):

- Jarvis\
  - Jarvis.Desktop.exe
  - (framework and runtime files)
  - backend\
	- python\
	  - python.exe
	  - (python libs)
	- app\
	  - (FastAPI backend code)
	- logs\

WiX Notes:
- Use heat.exe to harvest the backend folder and include it in your WiX project.
- Keep ownership and ACLs standard; do not install the backend as a service initially. Run it as a user process launched by the desktop app.
