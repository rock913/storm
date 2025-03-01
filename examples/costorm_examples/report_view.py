# pages/report_viewer.py
import streamlit as st
import requests
import os

def show_report():
    st.title("研究报告查看器")
    
    session_id = st.session_state.session_id
    response = requests.get(f"http://localhost:5000/api/sessions/{session_id}/report")
    
    if response.status_code == 200:
        report_path = os.path.join(DEMO_WORKING_DIR, f"{session_id}/report.md")
        with open(report_path, "r") as f:
            st.markdown(f.read())
    else:
        st.error("无法加载报告")

if __name__ == "__main__":
    show_report()