import streamlit as st
from pymongo import MongoClient
import urllib.parse
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from google.cloud import speech
import os
import time
import openai

# Connect to MongoDB
username = urllib.parse.quote_plus("demanualteam")
password = urllib.parse.quote_plus("Demanual@1235!")
uri = f"mongodb+srv://{username}:{password}@medical-transcription.xfonp.mongodb.net/?retryWrites=true&w=majority&appName=medical-transcription"

client = MongoClient(uri)
db = client["medical-transcription-auth"]
collection = db["auth-collection"]

def authenticate_user(username, password):
    try:
        user = collection.find_one({"username": username, "password": password})
        return user is not None
    except Exception as e:
        print(f"An error occurred: {e}")  # Log the error for debugging
        st.error("An error occurred during authentication. Please try again.")
        return False

def transcribe_audio():
    st.sidebar.title("API Setup")
    st.sidebar.expander("Expand", expanded=True)
    service_option = st.sidebar.selectbox("Select Transcription Service", ("Speechmatics", "Google Cloud Speech-to-Text", "OpenAI"), key="transcription_service")
    language_option = st.sidebar.radio("Select Language (Accent)", ("Australia", "American", "British"))

    if service_option == "Google Cloud Speech-to-Text":
        credentials_file = st.sidebar.file_uploader("Upload credentials.json", type=["json"])
        api_key = None
    else:
        api_key = st.sidebar.text_input("Enter API Key")

    if service_option == "Speechmatics":
        accuracy_option = st.sidebar.radio("Select Accuracy Level", ("Enhanced", "Standard"))

    st.title("Upload your audio to transcribe:")
    uploaded_file = st.file_uploader("")

    if uploaded_file is not None:
        if st.button("Transcribe"):
            if service_option == "Speechmatics":
                transcribe_with_speechmatics(uploaded_file, language_option, api_key, accuracy_option)
            elif service_option == "Google Cloud Speech-to-Text":
                if credentials_file is not None:
                    credentials = credentials_file.read()
                    transcribe_with_google(uploaded_file, language_option, credentials)
            elif service_option == "OpenAI":
                # Call the function to transcribe with OpenAI
                transcribe_with_openai(uploaded_file)

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
    audio_filename = "uploaded_audio" + os.path.splitext(audio_file.name)[1]  # Preserve file extension
    with open(audio_filename, "wb") as f:
        f.write(audio_file.read())

    # Initialize the Speechmatics BatchClient
    with BatchClient(settings) as client:
        try:
            # Submit the transcription job to Speechmatics
            job_id = client.submit_job(
                audio=(audio_filename, open(audio_filename, "rb")),
                transcription_config=conf,
            )

            # Wait for the transcription job to complete
            transcript = client.wait_for_completion(job_id, transcription_format="txt")
            st.write("Transcribed Text (Speechmatics):")
            st.write(transcript)
        except Exception as e:
            st.write("Error transcribing with Speechmatics:", e)
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

    return transcript

def logout():
    st.session_state["logged_in"] = False
    st.session_state["api_key"] = None
    st.success("Logged out successfully!")
    
def main():
    placeholder = st.empty()
    # Session state for login status and API key
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = None
        

    # Login form (displayed conditionally)
    if not st.session_state["logged_in"]:
        with placeholder.form("login"):
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

        # Check if API key needs to be provided
        if service_option != "Google Cloud Speech-to-Text":
            st.sidebar.title("API Key")
            api_key = st.sidebar.text_input("Enter API Key", st.session_state["api_key"] or "")
            st.session_state["api_key"] = api_key

        # Additional options for Speechmatics
        if service_option == "Speechmatics":
            accuracy_option = st.sidebar.radio("Select Accuracy Level", ("Enhanced", "Standard"))

        # Main transcribing functionality
        st.title("Upload your audio to transcribe:")
        uploaded_file = st.file_uploader("")

        if uploaded_file is not None:
            if st.button("Transcribe"):
                if service_option == "Speechmatics":
                    transcribe_with_speechmatics(uploaded_file, language_option, st.session_state["api_key"], accuracy_option)
                elif service_option == "Google Cloud Speech-to-Text":
                    credentials_file = st.sidebar.file_uploader("Upload credentials.json", type=["json"])
                    if credentials_file is not None:
                        credentials = credentials_file.read()
                        transcribe_with_google(uploaded_file, language_option, credentials)
                elif service_option == "OpenAI":
                    transcribe_with_openai(uploaded_file, st.session_state["api_key"])

# Run the Streamlit app
if __name__ == "__main__":
    main()
