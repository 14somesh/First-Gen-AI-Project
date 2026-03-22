@echo off
echo ===================================================
echo Starting AI Restaurant Recommendation Service Locally
echo ===================================================

echo.
echo [1] Starting FastAPI server on http://localhost:8000 ...
start "FastAPI Server" cmd /k "python -m uvicorn api.phase5_api:app --reload"

echo [2] Starting Streamlit App on http://localhost:8501 ...
start "Streamlit App" cmd /k "python -m streamlit run streamlit_app/app.py"


echo.
echo Both services have been launched in separate windows!
echo - FastAPI UI/Docs: http://localhost:8000 or http://localhost:8000/docs
echo - Streamlit App: http://localhost:8501
echo.
echo You can close this window now. To stop the servers, just close their respective windows.
pause
