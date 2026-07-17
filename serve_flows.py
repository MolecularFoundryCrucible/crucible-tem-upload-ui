"""
Registers Prefect flows as deployments and serves them.

Usage:
    export PREFECT_API_URL=http://127.0.0.1:4200/api
    python serve_flows.py
"""
import os
os.environ['PREFECT_LOGGING_EXTRA_LOGGERS'] = "prefect_backend"
from prefect import serve
from prefect_backend import run_shell, multi_file_upload, session_upload, upload_dataset, multi_assignment_upload

if __name__ == "__main__":
    multi_deploy = multi_file_upload.to_deployment(name="multi-file-upload")
    session_deploy = session_upload.to_deployment(name="session-upload")
    upload_deploy = upload_dataset.to_deployment(name="upload-dataset")
    ma_deploy = multi_assignment_upload.to_deployment(name="multi-assignment-upload")
    serve(multi_deploy, session_deploy, upload_deploy, ma_deploy, limit=10)
