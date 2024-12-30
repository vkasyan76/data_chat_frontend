import streamlit as st
import requests
import pandas as pd
import os
import base64

# Set up the app layout
st.set_page_config(layout="wide")

# Backend URL (FastAPI server) fetched from Streamlit secrets
BACKEND_URL = st.secrets["BACKEND_URL"]  # Ensure this is set in Streamlit secrets

# ---------------------------
# Function to Add Custom CSS from styles.css
# ---------------------------
def add_custom_css(css_file_path):
    """
    Reads a CSS file and injects it into the Streamlit app.

    Parameters:
    - css_file_path (str): The path to the CSS file.
    """
    if os.path.exists(css_file_path):
        with open(css_file_path) as f:
            css = f.read()
            st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {css_file_path}")

# Hide the submit button in forms
hide_submit_button_css = """
    <style>
    form [type=submit] {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_submit_button_css, unsafe_allow_html=True)

def get_image_base64(image_path):
    """
    Encodes an image file to a base64 string.
    
    Parameters:
    - image_path (str): Path to the image file.
    
    Returns:
    - str: Base64 encoded string of the image.
    """
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        st.error(f"Error encoding image: {e}")
        return ""

# Path to your image
image_path = os.path.join("images", "HightechData.jpg")  # Adjust the path if necessary

# Encode the image
image_base64 = get_image_base64(image_path)

# Path to your CSS file
css_path = os.path.join("assets", "styles.css")  # Adjust the path if needed
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Inject the CSS
add_custom_css(css_path)

# ---------------------------
# 1) TOP SECTION: Fixed Navbar with Title and Icon
# ---------------------------

# Render Fixed Navbar
st.markdown(
    f"""
    <div class="navbar">
        <div style="display: flex; align-items: center; width: 100%;">
            <img src="data:image/jpeg;base64,{image_base64}" alt="Logo">
            <h1>AI-Powered Data Chat</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# ---------------------------
# 2) MIDDLE SECTION: File Upload & Data Display
# ---------------------------

user_df = None

# Initialize session state for data source visibility
if 'data_source_visible' not in st.session_state:
    st.session_state.data_source_visible = True

if 'current_data' not in st.session_state:
    st.session_state.current_data = None

# Initialize session state for chat history if not exists
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Upload and process user data
def process_user_data(uploaded_file):
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)

        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            # Convert all datetime columns to string (ISO format)
            for col in df.select_dtypes(include=['datetime64', 'datetime']):
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            st.error("Unsupported file format. Please upload a CSV or Excel file.")
            return None
        
        # Ensure all object type columns are treated as strings to maintain consistency
        object_cols = df.select_dtypes(include=['object']).columns
        for col in object_cols:
            df[col] = df[col].astype(str)
        
        # Sanitize for NaN, inf values to avoid JSON serialization errors 
        df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
        df.fillna(0, inplace=True)

        return df
    except Exception as e:
        st.error(f"Failed to process the file. Error: {str(e)}")
        return None

def fetch_airtable_data():
    try:
        response = requests.get(f"{BACKEND_URL}/")
        if response.status_code == 200:
            data = response.json()["data"]
            return pd.DataFrame(data)
        else:
            st.error("Failed to fetch data from Airtable")
            return None
    except Exception as e:
        st.error(f"Error fetching Airtable data: {str(e)}")
        return None

def clear_data():
    st.session_state.current_data = None
    st.session_state.data_source_visible = True
    st.session_state.chat_history = []

# Data Source Selection Interface using Drop-Down Menu
if st.session_state.data_source_visible:
    # Define the options for the selectbox
    data_source_options = ["Select an option", "Upload data (CSV or Excel file)", "Use pre-loaded data"]
    
    # Create a selectbox for data source selection
    selected_option = st.selectbox("Data Source:", options=data_source_options)
    
    if selected_option == "Upload data (CSV or Excel file)":
        st.markdown("### Upload data (CSV or Excel file)")
        uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
        if uploaded_file:
            with st.spinner("Processing file..."):
                user_df = process_user_data(uploaded_file)
                if user_df is not None:
                    st.session_state.current_data = user_df
                    st.session_state.data_source_visible = False
                    st.rerun()  # Use st.rerun() as per your Streamlit version
    
    elif selected_option == "Use pre-loaded data":
        if st.button("Load Data"):
            with st.spinner("Fetching Airtable data..."):
                airtable_df = fetch_airtable_data()
                if airtable_df is not None:
                    st.session_state.current_data = airtable_df
                    st.session_state.data_source_visible = False
                    st.rerun()

# Display the loaded data if available
if st.session_state.current_data is not None:
    # Create two main columns: Left (input and chat), Right (data and clear button)
    left_col, right_col = st.columns([2, 3])  # Adjust the ratio as needed

    with left_col:
        # User input using a form
        with st.form(key='chat_form', clear_on_submit=True):
            user_question = st.text_input(
                "Ask a question about the uploaded data and hit Enter:",
                placeholder="Type your question here..."
            )
            submit_button = st.form_submit_button(label='Submit')

        if submit_button and user_question.strip():
            # Add user question to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_question})

            # Send the question to the backend
            with st.spinner("Fetching the answer..."):
                try:
                    limited_history = st.session_state.chat_history[-10:]
                    response = requests.post(
                        f"{BACKEND_URL}/userdata_query/",
                        json={
                            "question": user_question,
                            "data": st.session_state.current_data.to_dict(orient="records"),
                            "history": limited_history
                        }
                    )

                    if response.status_code == 200:
                        answer = response.json().get("answer", "I couldn't find the answer. Try rephrasing or asking a different question.")
                        # Append the answer to chat history
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    else:
                        error_detail = response.json().get("detail", "Unknown error.")
                        st.error(f"Error: {error_detail}")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

        # Chat history within the same container
        if len(st.session_state.chat_history) > 0:
            # Chat container (scrollable)
            chat_html_list = [
            """
            <div class="scrollable-chat">
            """
            ]
            # Reverse chat history in chunks of two (Q + A)
            for i in range(len(st.session_state.chat_history) - 1, -1, -2):
                # Display User question first
                user_msg = st.session_state.chat_history[i - 1] if i > 0 else None
                ai_msg = st.session_state.chat_history[i]
                
                if user_msg and user_msg['role'] == 'user':
                    chat_html_list.append(
                        f"<div class='chat-message-user'><b>User:</b> {user_msg['content']}</div>"
                    )
                if ai_msg['role'] == 'assistant':
                    chat_html_list.append(
                        f"<div class='chat-message-ai'><b>AI:</b> {ai_msg['content']}</div>"
                    )
            
            # Append closing div and scrolling script
            chat_html_list.append("""
            </div>
            <script>
            var chatDiv = window.parent.document.querySelector('.scrollable-chat');
            if (chatDiv) chatDiv.scrollTop = 0;  // Keep scroll at the top
            </script>
            """)

            # Join the list to produce final HTML
            chat_html = "".join(chat_html_list)
            st.markdown(chat_html, unsafe_allow_html=True)

            # Clear Chat Button with unique key
            if st.button("Clear Chat", key="clear_chat_button_unique"):
                st.session_state.chat_history = []
                st.rerun()  # Use st.rerun() as per your Streamlit version

    with right_col:
        # Add a clear button that looks like an X in the top right
        if st.button("✖️", help="Clear current data"):
            clear_data()
            st.rerun()  # Use st.rerun() as per your Streamlit version

        # Display the data table
        st.dataframe(st.session_state.current_data, height=650, use_container_width=True)

# Footer Section
footer_html = """
    <div class="footer">
        AdvantiStar © 2025 | www.data-chat-ai.streamlit.app
    </div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
