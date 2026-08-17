import streamlit as st
import requests


st.set_page_config(
    page_title="Enterprise AI Operations Assistant",
    layout="wide"
)

API_URL = "http://127.0.0.1:8000"


if "token" not in st.session_state:
    st.session_state.token = None

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------
# Header
# --------------------------------------------------

st.title("Enterprise AI Operations Assistant")

st.caption(
    "Authorization-aware AI assistant for enterprise information, "
    "business data analysis, and controlled operations."
)


# --------------------------------------------------
# Login
# --------------------------------------------------

if not st.session_state.token:

    st.subheader("Sign in")

    username = st.text_input(
        "Username",
        placeholder="Enter your username"
    )

    password = st.text_input(
        "Password",
        type="password",
        placeholder="Enter your password"
    )

    if st.button("Sign in", type="primary"):

        response = requests.post(
            f"{API_URL}/login",
            json={
                "username": username,
                "password": password
            }
        )

        if response.status_code == 200:

            data = response.json()

            st.session_state.token = data["access_token"]

            st.rerun()

        else:

            st.error("Authentication failed.")

    st.stop()


# --------------------------------------------------
# Authenticated workspace
# --------------------------------------------------

st.success("Authenticated")

st.divider()


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.header("Workspace")

    st.markdown(
        """
        **AI capabilities**

        • Business information  
        • Report understanding  
        • CSV analysis  
        • CSV comparison  
        • Authorized operations
        """
    )

    st.divider()

    if st.button("Log out"):

        st.session_state.token = None
        st.session_state.messages = []

        st.rerun()


# --------------------------------------------------
# Main workspace
# --------------------------------------------------

st.subheader("Business Operations Workspace")

st.markdown(
    """
    Select what you want to accomplish. The assistant will
    use the appropriate authorized capability.
    """
)

operation = st.radio(
    "Operation",
    [
        "Understand information",
        "Analyze report",
        "Compare reports",
        "Authorized operation"
    ],
    horizontal=True
)


# --------------------------------------------------
# Chat history
# --------------------------------------------------

for sender, message in st.session_state.messages:

    if sender == "You":

        with st.chat_message("user"):
            st.write(message)

    else:

        with st.chat_message("assistant"):
            st.write(message)


# --------------------------------------------------
# Chat input
# --------------------------------------------------

message = st.chat_input(
    "Ask about your work, reports, or business data..."
)


if message:

    st.session_state.messages.append(
        ("You", message)
    )

    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    try:

        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": message
            },
            headers=headers
        )

        if response.status_code == 200:

            data = response.json()

            answer = data.get(
                "response",
                "No response returned."
            )

            st.session_state.messages.append(
                ("AI", answer)
            )

        elif response.status_code == 401:

            st.error("Your session has expired. Please sign in again.")

        elif response.status_code == 403:

            st.error(
                "You are not authorized to perform this operation."
            )

        else:

            st.error(
                f"Request failed: {response.status_code}"
            )

    except requests.RequestException:

        st.error(
            "Unable to connect to the AI backend."
        )

    st.rerun()

# --------------------------------------------------
# Business Data Workspace
# --------------------------------------------------

st.divider()

if operation == "Understand information":

    st.subheader("💬 Information Request")

    information_request = st.text_area(
        "What would you like to understand?",
        placeholder=(
            "Example: Explain the key information in this business report."
        ),
        height=120
    )

    if st.button("Submit request", type="primary"):

        headers = {
            "Authorization": f"Bearer {st.session_state.token}"
        }

        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": information_request
            },
            headers=headers
        )

        if response.status_code == 200:

            data = response.json()

            st.subheader("AI Result")
            st.write(data.get("response", "No response returned."))

        elif response.status_code == 403:

            st.error(
                "You are not authorized to perform this operation."
            )

        else:

            st.error(
                f"Request failed: {response.status_code}"
            )


elif operation == "Analyze report":

    st.subheader("📊 Analyze Business Report")

    uploaded_file = st.file_uploader(
        "Upload a CSV report",
        type=["csv"],
        key="analyze_csv"
    )

    analysis_request = st.text_area(
        "What would you like to know about this report?",
        placeholder=(
            "Example: Analyze the sales data and summarize the important information."
        ),
        height=120
    )

    if st.button("Analyze report", type="primary"):

        if uploaded_file is None:

            st.warning("Please upload a CSV report first.")

        elif not analysis_request.strip():

            st.warning("Please describe what you want to know.")

        else:

            headers = {
                "Authorization": f"Bearer {st.session_state.token}"
            }

            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "text/csv"
                )
            }

            upload_response = requests.post(
                f"{API_URL}/upload-csv",
                files=files,
                headers=headers
            )

            if upload_response.status_code == 200:

                upload_data = upload_response.json()
                print("UPLOAD RESPONSE:", upload_data)

                stored_file_path = upload_data["path"]

                analysis_message = (
                    f"Analyze the uploaded CSV file at "
                    f"{stored_file_path}. "
                    f"User request: {analysis_request}"
                )

                result = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "message": analysis_message
                    },
                    headers=headers
                )

                if result.status_code == 200:

                    data = result.json()

                    st.subheader("AI Result")

                    st.write(
                        data.get(
                            "response",
                            "No response returned."
                        )
                    )

                elif result.status_code == 403:

                    st.error(
                        "You are not authorized to perform this operation."
                    )

                else:

                    st.error(
                        f"AI request failed: {result.status_code}"
                    )

            else:

                st.error(
                    f"CSV upload failed: {upload_response.status_code}"
                )


elif operation == "Compare reports":

    st.subheader("📈 Compare Business Reports")

    file1 = st.file_uploader(
        "Upload first CSV report",
        type=["csv"],
        key="compare_csv_1"
    )

    file2 = st.file_uploader(
        "Upload second CSV report",
        type=["csv"],
        key="compare_csv_2"
    )

    comparison_request = st.text_area(
        "What would you like to compare?",
        placeholder=(
            "Example: Compare these two sales reports and explain the differences."
        ),
        height=120
    )

    if st.button("Compare reports", type="primary"):

        if file1 is None or file2 is None:

            st.warning("Please upload both CSV reports.")

        elif not comparison_request.strip():

            st.warning("Please describe what you want to compare.")

        else:

            headers = {
                "Authorization": f"Bearer {st.session_state.token}"
            }

            files1 = {
                "file": (
                    file1.name,
                    file1.getvalue(),
                    "text/csv"
                )
            }

            files2 = {
                "file": (
                    file2.name,
                    file2.getvalue(),
                    "text/csv"
                )
            }

            upload1 = requests.post(
                f"{API_URL}/upload-csv",
                files=files1,
                headers=headers
            )

            upload2 = requests.post(
                f"{API_URL}/upload-csv",
                files=files2,
                headers=headers
            )

            if upload1.status_code == 200 and upload2.status_code == 200:

                comparison_message = (
                    f"Compare these two uploaded CSV files: "
                    f"data/uploads/{file1.name} and "
                    f"data/uploads/{file2.name}. "
                    f"User request: {comparison_request}"
                )

                result = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "message": comparison_message
                    },
                    headers=headers
                )

                if result.status_code == 200:

                    data = result.json()

                    st.subheader("AI Result")

                    st.write(
                        data.get(
                            "response",
                            "No response returned."
                        )
                    )

                elif result.status_code == 403:

                    st.error(
                        "You are not authorized to perform this operation."
                    )

                else:

                    st.error(
                        f"AI request failed: {result.status_code}"
                    )

            else:

                st.error("One or both CSV uploads failed.")


elif operation == "Authorized operation":

    st.subheader("🔐 Authorized Enterprise Operation")

    operation_request = st.text_area(
        "Describe the operation you want to perform",
        placeholder=(
            "Example: Perform an operation on an enterprise resource "
            "that I am authorized to access."
        ),
        height=120
    )

    if st.button("Execute operation", type="primary"):

        if not operation_request.strip():

            st.warning("Please describe the operation.")

        else:

            headers = {
                "Authorization": f"Bearer {st.session_state.token}"
            }

            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "message": operation_request
                },
                headers=headers
            )

            if response.status_code == 200:

                data = response.json()

                st.subheader("Operation Result")

                st.write(
                    data.get(
                        "response",
                        "No response returned."
                    )
                )

            elif response.status_code == 403:

                st.error(
                    "You are not authorized to perform this operation."
                )

            else:

                st.error(
                    f"Request failed: {response.status_code}"
                )