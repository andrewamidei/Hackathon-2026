.\venv\Scripts\python -m pip install -r requirements.txt
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd src; ..\venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8001 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\venv\Scripts\python -m streamlit run src\main.py"
