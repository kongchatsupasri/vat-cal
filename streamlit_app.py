import streamlit as st
from google_auth_oauthlib.flow import Flow
import json

# Detect environment (Local or Streamlit Cloud)
if "GOOGLE_CLIENT_ID" in st.secrets:
    st.write('aaa')
    st.write(st.secrets)
    CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://vat-cal.streamlit.app/"
else:
    st.write('bbb')
    st.write(st.secrets)
    CLIENT_ID = "your-local-client-id.apps.googleusercontent.com"
    CLIENT_SECRET = "your-local-client-secret"
    REDIRECT_URI = "http://localhost:8501/"

st.title("Google Login with Streamlit")

# Create OAuth flow
flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    },
    scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
    redirect_uri=REDIRECT_URI
)

auth_url, state = flow.authorization_url(prompt="consent")

st.write("Click below to log in with Google:")
st.markdown(f'<a href="{auth_url}" target="_self"><button>Login with Google</button></a>', unsafe_allow_html=True)
