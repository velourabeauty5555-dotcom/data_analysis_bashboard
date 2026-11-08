# Data Analysis Dashboard

## Included
- `app.py`: starter entry point for the Streamlit dashboard
- `app.py.py`: actual dashboard implementation
- `requirements.txt`: required Python packages

## Run in VS Code on Windows 11
1. Open VS Code → File → Open Folder → choose this folder.
2. Open Terminal → New Terminal.
3. Run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, use Command Prompt instead:

```cmd
.venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run app.py
```

The app opens at the local address printed in the terminal, usually http://localhost:8501.

## Suggested columns
For all dashboard panels to populate automatically, use headings such as:
- Invoice Number
- Date
- City
- Invoice Total (numeric)
- Profit (numeric)

The app tries to detect likely columns by heading. You can also choose the sales and profit columns in the sidebar. If a date or city heading is not detected, rename it to Date or City.

The dashboard is a practical template; verify calculations and filters before using reports for business decisions.
