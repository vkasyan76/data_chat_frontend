import streamlit as st
import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Backend URL from environment variable
# BACKEND_URL = os.getenv("BACKEND_URL")

# Fetch BACKEND_URL from secrets
BACKEND_URL = st.secrets["BACKEND_URL"]

# Set up the app layout
st.set_page_config(layout="wide")

# Backend URL (FastAPI server)
# BACKEND_URL = "http://127.0.0.1:8000"  

# Fetch the data from the FastAPI server
@st.cache_data(show_spinner=False)
def fetch_data():
    response = requests.get(f"{BACKEND_URL}/")
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        st.error("Failed to fetch data from the backend.")
        return []

data = fetch_data()

# Create two columns
col1, col2 = st.columns([1, 2])  # Adjust width ratios as needed

# Column 1: Question Input and Answer
with col1:
    st.subheader("Data Query")
    user_question = st.text_input(
        "Enter your question and hit enter",
        placeholder="What is the profit after tax of Pine Road store for dog foods, if tax rate is 30%?",
        key="user_question_input"
    )

    # Placeholder for the answer
    answer_placeholder = st.empty()

    # Check for user input and fetch the answer
    if user_question:
        with st.spinner("Fetching the answer..."):
            try:
                response = requests.post(f"{BACKEND_URL}/query/", json={"question": user_question})
                if response.status_code == 200:
                    answer = response.json().get("answer", "No answer returned.")
                    answer_placeholder.success(answer)
                else:
                    answer_placeholder.error(f"Error: {response.json().get('detail', 'Failed to fetch the answer.')}")
            except Exception as e:
                answer_placeholder.error(f"Error: {str(e)}")

# Column 2: Data Preview
with col2:
    st.subheader("Raw Data")
    if data:
        st.dataframe(data)
    else:
        st.write("No data available.")
