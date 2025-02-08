import streamlit as st
from google_auth_oauthlib.flow import Flow
import json

# Detect environment (Local or Streamlit Cloud)
if "GOOGLE_CLIENT_ID" in st.secrets:
    st.write(st.secrets)
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://your-app-name.streamlit.app/"
else:
    CLIENT_ID = "your-local-client-id.apps.googleusercontent.com"
    CLIENT_SECRET = "your-local-client-secret"
    REDIRECT_URI = "http://localhost:8501/"


