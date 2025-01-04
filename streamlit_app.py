# streamlit_app.py

import streamlit as st
import requests
import pandas as pd
import os
import base64
import matplotlib.pyplot as plt

# ---------------------------
# Helper Functions
# ---------------------------

def add_custom_css(css_file_path):
    """
    Reads a CSS file and injects it into the Streamlit app.
    """
    if os.path.exists(css_file_path):
        with open(css_file_path) as f:
            css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {css_file_path}")

def get_image_base64(image_path):
    """
    Encodes an image file to a base64 string.
    """
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        st.error(f"Error encoding image: {e}")
        return ""

def process_user_data(uploaded_file):
    """
    Processes the uploaded CSV or Excel file and returns a DataFrame.
    """
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

def fetch_airtable_data(backend_url):
    """
    Fetches pre-loaded data from the backend server.
    """
    try:
        response = requests.get(f"{backend_url}/")
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
    """
    Clears the current data and resets the session state.
    """
    st.session_state.current_data = None
    st.session_state.data_source_visible = True
    st.session_state.chat_history = []
    st.session_state.chart_history = []
    st.session_state.selected_tab = "Conversation"

# ---------------------------
# Streamlit App Configuration
# ---------------------------

# Set up the app layout
st.set_page_config(layout="wide", page_title="AI-Powered Data Chat & Chart Generator")

# Backend URL (FastAPI server)
# Replace with your backend URL if different
BACKEND_URL = st.secrets["BACKEND_URL"]  # Ensure this is set in Streamlit secrets

# Inject custom CSS
css_path = os.path.join("assets", "styles.css")
add_custom_css(css_path)

# Hide the submit button in forms
hide_submit_button_css = """
    <style>
    form [type=submit] {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_submit_button_css, unsafe_allow_html=True)

# Encode the navbar image
image_path = os.path.join("images", "HightechData.jpg")
image_base64 = get_image_base64(image_path)

# Render Fixed Navbar
st.markdown(
    f"""
    <div class="navbar">
        <div style="display: flex; align-items: center; width: 100%;">
            <img src="data:image/jpeg;base64,{image_base64}" alt="Logo">
            <h1>AI-Powered Data Chat & Chart Generator</h1>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Initialize Session State
# ---------------------------
if 'data_source_visible' not in st.session_state:
    st.session_state.data_source_visible = True

if 'current_data' not in st.session_state:
    st.session_state.current_data = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'chart_history' not in st.session_state:
    st.session_state.chart_history = []

if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "Chart Generation"

# ---------------------------
# Main Content Area
# ---------------------------

# Remove horizontal rule to minimize spacing
# st.markdown("---")  # Removed to reduce vertical space

# Create a single row with two columns: left and right
left_col, right_col = st.columns([2, 3], gap="small")

with left_col:
    # Mode Selection Dropdown with no label
    mode_options = ["Conversation", "Chart Generation"]
    selected_mode = st.selectbox("", options=mode_options, index=1, key="mode_selection")
    st.session_state.selected_tab = selected_mode  # Update session state

    # Depending on selected_tab and data loaded, show forms
    if st.session_state.current_data is None:
        # Show disabled forms with a prompt to load data
        if st.session_state.selected_tab == "Conversation":
            # Conversation Form (Disabled)
            with st.form(key='chat_form', clear_on_submit=True):
                user_question = st.text_input(
                    "Ask a question about the uploaded data and hit Enter:",
                    placeholder="Type your question here...",
                    disabled=True
                )
                submit_button = st.form_submit_button(label='Submit', disabled=True)
            st.info("Please load data from the right to enable the conversation.")
        elif st.session_state.selected_tab == "Chart Generation":
            # Chart Generation Form (Disabled)
            with st.form(key="chart_form", clear_on_submit=True):
                instruction = st.text_input(
                    "Chart Instruction",
                    placeholder="Type your chart requirement here...",
                    disabled=True
                )
                ctype = st.selectbox("Select chart type:", ["Bar","Area","Pie", "Line", "Scatter"], disabled=True)
                gen_btn = st.form_submit_button("Generate Chart", disabled=True)
            st.info("Please load data from the right to enable chart generation.")
    else:
        if st.session_state.selected_tab == "Conversation":
            # st.markdown("### Conversation")
            # Conversation Form
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
                # Iterate through chat history in pairs (User and Assistant)
                for i in range(0, len(st.session_state.chat_history), 2):
                    user_msg = st.session_state.chat_history[i]
                    ai_msg = st.session_state.chat_history[i + 1] if i + 1 < len(st.session_state.chat_history) else None
                    
                    if user_msg and user_msg['role'] == 'user':
                        chat_html_list.append(
                            f"<div class='chat-message-user'><b>User:</b> {user_msg['content']}</div>"
                        )
                    if ai_msg and ai_msg['role'] == 'assistant':
                        chat_html_list.append(
                            f"<div class='chat-message-ai'><b>AI:</b> {ai_msg['content']}</div>"
                        )
                
                # Append closing div and scrolling script
                chat_html_list.append("""
                </div>
                <script>
                var chatDiv = window.parent.document.querySelector('.scrollable-chat');
                if (chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;  // Scroll to bottom
                </script>
                """)

                # Join the list to produce final HTML
                chat_html = "".join(chat_html_list)
                st.markdown(chat_html, unsafe_allow_html=True)

                # Clear Chat Button with unique key
                if st.button("Clear Chat", key="clear_chat_button_unique"):
                    st.session_state.chat_history = []
                    st.rerun()

        elif st.session_state.selected_tab == "Chart Generation":
            # st.markdown("### Chart Generation")
            # Chart generation form
            with st.form(key="chart_form", clear_on_submit=True):
                instruction = st.text_input(
                    "Chart Instruction",
                    placeholder="Type your chart requirement here...",
                    key="chart_instruction_input"
                )
                ctype = st.selectbox("Select chart type:", ["Bar","Area","Pie", "Line", "Scatter"])
                gen_btn = st.form_submit_button("Generate Chart")
    
            if gen_btn and instruction.strip():
                with st.spinner("Generating chart..."):
                    df_records = st.session_state.current_data.to_dict(orient="records")
                    payload = {
                        "instruction": instruction,
                        "chart_type": ctype,
                        "data": df_records
                    }
                    try:
                        r = requests.post(f"{BACKEND_URL}/generate_chart/", json=payload)
                        if r.status_code == 200:
                            body = r.json()
                            df_list = body.get("df_final", [])
                            err = body.get("error")
                            if err:
                                st.error(err)
                            else:
                                df_final = pd.DataFrame(df_list)
                                st.session_state.chart_history.append({
                                    "instruction": instruction,
                                    "chart_type": ctype,
                                    "df_final": df_final
                                })
                        else:
                            det = r.json().get("detail","Unknown error.")
                            st.error(f"Error: {det}")
                    except Exception as e:
                        st.error("I'm sorry, I couldn't process your request. Please try rephrasing your question.")
    
            # Display generated charts
            if len(st.session_state.chart_history) > 0:
                for entry in reversed(st.session_state.chart_history):
                    st.markdown(f"**Instruction**: {entry['instruction']}")
                    st.markdown(f"**Chart Type**: {entry['chart_type']}")
    
                    df_chart = entry["df_final"]
    
                    # 1) Check if df_chart is empty or has no columns
                    if df_chart.empty or df_chart.shape[1] == 0:
                        st.error("No data found. Please try rephrasing your question.")
                        st.markdown("---")
                        continue
                    
                    # If there's an Error column, display it
                    if "Error" in df_chart.columns:
                        st.error(df_chart["Error"].iloc[0])
                        st.markdown("---")
                        continue
    
                    # Display the chart using Streamlit or Matplotlib (for pie)
                    chart_type = entry["chart_type"].lower()
                    if chart_type == "bar":
                        st.bar_chart(df_chart.set_index(df_chart.columns[0]))
                    elif chart_type == "area":
                        st.area_chart(df_chart.set_index(df_chart.columns[0]))
                    elif chart_type == "line":
                        st.line_chart(df_chart.set_index(df_chart.columns[0]))
                    elif chart_type == "scatter":
                        st.scatter_chart(df_chart.set_index(df_chart.columns[0]))
                    elif chart_type == "pie":
                        if df_chart.empty:
                            st.warning("No data to display for a pie chart.")
                        else:
                            labels = df_chart.iloc[:, 0].astype(str).tolist()
                            values = df_chart.iloc[:, 1].astype(float).tolist()
    
                            # NEW CHECK: Ensure all values are non-negative
                            if any(v < 0 for v in values):
                                st.error("Cannot plot negative values on a pie chart. Please try another chart type or adjust the data.")
                                st.markdown("---")
                                continue
    
                            # If everything is good, build the pie chart
                            fig, ax = plt.subplots()
                            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
                            ax.axis("equal")
                            st.pyplot(fig)
                    else:
                        st.dataframe(df_chart)
    
                    st.markdown("---")

with right_col:
    if st.session_state.data_source_visible:
        # st.subheader("Data Source Selection")
        
        # Define the options for the selectbox
        data_source_options = ["Select an option", "Upload data (CSV or Excel file)", "Use pre-loaded data"]
        
        # Create a selectbox for data source selection
        selected_option = st.selectbox("", options=data_source_options, key="data_source_selection")
        
        if selected_option == "Upload data (CSV or Excel file)":
            st.markdown("### Upload CSV or Excel File")
            uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
            if uploaded_file:
                with st.spinner("Processing file..."):
                    user_df = process_user_data(uploaded_file)
                    if user_df is not None:
                        st.session_state.current_data = user_df
                        st.session_state.data_source_visible = False
                        st.session_state.selected_tab = "Conversation"
                        st.rerun()  # Refresh the app state
        elif selected_option == "Use pre-loaded data":
            if st.button("Load Pre-loaded Data"):
                with st.spinner("Fetching Airtable data..."):
                    airtable_df = fetch_airtable_data(BACKEND_URL)
                    if airtable_df is not None:
                        st.session_state.current_data = airtable_df
                        st.session_state.data_source_visible = False
                        st.session_state.selected_tab = "Conversation"
                        st.rerun()
    else:
        if st.session_state.current_data is not None:
            # Display the Clear Data button above the data table with minimal spacing
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("✖️", help="Clear data & charts"):
                clear_data()
                st.rerun()
            
            # Display the data table
            st.dataframe(st.session_state.current_data, height=750, use_container_width=True)
        else:
            # If no data is loaded, provide a prompt or leave blank
            st.warning("No data loaded. Please select a data source from the dropdown.")

# ---------------------------
# Footer Section
# ---------------------------
footer_html = """
    <div class="footer">
        AdvantiStar © 2025 | www.data-chat-ai.streamlit.app
    </div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
