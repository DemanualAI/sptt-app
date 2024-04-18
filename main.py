import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from google.cloud import speech
import os
import json
import openai
import supabase
from google.oauth2.service_account import Credentials as GoogleCredentials

# Initialize Supabase client
supabase_url = "https://cxubvlwhxxdwvfwtofgv.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dWJ2bHdoeHhkd3Zmd3RvZmd2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTE4MTA0NjQsImV4cCI6MjAyNzM4NjQ2NH0.Wbmni2Rh_B5Bx5ipcCzoeMX-5Bn5PrnMVfMXCeEYvZw"
supabase_client = supabase.create_client(supabase_url, supabase_key)

def authenticate_user(users_email, users_password):
    try:
        # Sign in with email and password
        user = supabase_client.auth.sign_in_with_password({ "email": users_email, "password": users_password })
        return True
    except Exception as e:
        print(f"An error occurred during authentication: {e}")
        st.error("An error occurred during authentication. Please try again.")
        return False

def transcribe_with_speechmatics(audio_file, language_code, api_key, operating_point):
    # Speechmatics authentication token and other settings
    settings = ConnectionSettings(
        url="https://asr.api.speechmatics.com/v2",
        auth_token=api_key,
    )

    # Mapping language codes for different accents
    language_mapping = {
        "Australia": "en",
        "American": "en",
        "British": "en",
    }
    LANGUAGE = language_mapping[language_code]

    # Operating point configuration
    operating_point_mapping = {
        "Enhanced": "enhanced",
        "Standard": "standard",
    }
    OPERATING_POINT = operating_point_mapping[operating_point]

    # Spelling locale configuration
    locale_mapping = {
        "Australia": "en-AU",
        "American": "en-US",
        "British": "en-GB",
    }
    OUTPUT_LOCALE = locale_mapping[language_code]

    conf = {
        "type": "transcription",
        "transcription_config": {
            "language": LANGUAGE,
            "operating_point": OPERATING_POINT,
            "output_locale": OUTPUT_LOCALE,
        },
    }

    # Save the uploaded file locally
    audio_filename = audio_file.name  # Preserve file extension
    with open(audio_filename, "wb") as f:
        f.write(audio_file.read())

    # Initialize the Speechmatics BatchClient
    with BatchClient(settings) as client:
        try:
            # Submit the transcription job to Speechmatics
            with open(audio_filename, "rb") as audio_file:
                job_id = client.submit_job(
                    audio=(audio_filename, audio_file),
                    transcription_config=conf,
                )

            # Wait for the transcription job to complete
            transcript = client.wait_for_completion(job_id, transcription_format="txt")
            st.write(f"Transcribed Text (Speechmatics) for {audio_file.name}:")
            st.write(transcript)
        except Exception as e:
            st.write(f"Error transcribing with Speechmatics for {audio_file.name}:", e)
        finally:
            # Remove the temporary audio file
            os.remove(audio_filename)



def transcribe_with_google(audio_file, language_code, credentials):
    # Mapping language codes for different accents
    language_mapping = {
        "Australia": "en-AU",
        "American": "en-US",
        "British": "en-GB",
    }
    LANGUAGE = language_mapping[language_code]

    # Initialize Google Cloud Speech-to-Text client
    client = speech.SpeechClient(credentials=credentials)

    # Read the audio file content
    audio_content = audio_file.read()

    # Configure the recognition request
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(language_code=LANGUAGE)

    # Perform the transcription
    response = client.recognize(config=config, audio=audio)

    # Extract transcribed text
    transcribed_text = ""
    for result in response.results:
        transcribed_text += result.alternatives[0].transcript + "\n"
    
    st.write(f"Transcribed Text (Google cloud api) for {audio_file.name}:")
    st.write(transcribed_text)
    return transcribed_text

def transcribe_with_openai(audio_file, api_key):
    openai.api_key = api_key

    with open(audio_file.name, "rb") as file:
        transcript = openai.Audio.transcribe(
            file=file,
            model="whisper-1",
            response_format="text",
            language="en"
        )
    st.write(f"Transcribed Text (OpenAI) for {audio_file.name}:")
    st.write(transcript)
    return transcript

def logout():
    st.session_state["logged_in"] = False
    st.session_state["api_key"] = None
    st.success("Logged out successfully!")
    
def main():
    st.set_page_config(page_title="My Tab Title")
    placeholder = st.empty()
    # Session state for login status and API key
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = None
        

    # Login form (displayed conditionally)
    if not st.session_state["logged_in"]:
        with placeholder.form("login"):
            # Center align the image only on the login page
            st.image("images/logo-removebg-preview.png", use_column_width=True)

            st.title("Login")
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submit = st.form_submit_button()

        if submit:
            placeholder.empty()
            if authenticate_user(username_input, password_input):
                st.session_state["logged_in"] = True
                st.success("Logged in successfully!")
            else:
                placeholder.empty()
                st.error("Login failed. Please check your credentials.")
    
    # API setup (displayed only when logged in)
    if st.session_state["logged_in"]:
        # Logout button (displayed only when logged in)
        if st.session_state["logged_in"]:
            st.sidebar.button("Logout", on_click=logout)
            
        st.sidebar.title("API Setup")
        service_option = st.sidebar.selectbox("Select Transcription Service", ("Speechmatics", "Google Cloud Speech-to-Text", "OpenAI"), key="transcription_service")
        language_option = st.sidebar.radio("Select Language (Accent)", ("Australia", "American", "British"))
        
        # Main transcribing functionality
        st.title("Upload your audio to transcribe:")
        uploaded_files = st.file_uploader("Upload multiple files", accept_multiple_files=True)

        # Always display API Key input
        if service_option != "Google Cloud Speech-to-Text":
            st.sidebar.title("API Key")
            api_key = st.sidebar.text_input("Enter API Key", st.session_state["api_key"] or "")
            st.session_state["api_key"] = api_key

        # Check if API key needs to be provided
        if service_option == "Google Cloud Speech-to-Text":
            credentials_file = st.sidebar.file_uploader("Upload credentials.json", type=["json"])
            if credentials_file is not None:
                credentials = GoogleCredentials.from_service_account_info(
                    json.loads(credentials_file.read())
                )
                if st.button("Transcribe"):
                    for uploaded_file in uploaded_files:
                        transcribe_with_google(uploaded_file, language_option, credentials)
        else:
            # Additional options for Speechmatics
            if service_option == "Speechmatics":
                accuracy_option = st.sidebar.radio("Select Accuracy Level", ("Enhanced", "Standard"))

            if uploaded_files is not None:
                if st.button("Transcribe"):
                    for uploaded_file in uploaded_files:
                        if service_option == "Speechmatics":
                            transcribe_with_speechmatics(uploaded_file, language_option, st.session_state["api_key"], accuracy_option)
                        elif service_option == "OpenAI":
                            transcribe_with_openai(uploaded_file, st.session_state["api_key"])

# Run the Streamlit app
if __name__ == "__main__":
    main()
