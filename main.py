import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from google.cloud import speech
import os
import time


# Function to transcribe audio using Speechmatics API
def transcribe_with_speechmatics(audio_file, language_code):
    # Speechmatics authentication token and other settings
    AUTH_TOKEN = "Ga05ubU2YVpDWszudTLevzUbMBwMPPuE"
    
    # Mapping language codes for different accents
    language_mapping = {
        "Australia": "en",
        "American": "en",
        "British": "en",
    }
    
    LANGUAGE = language_mapping[language_code]

    settings = ConnectionSettings(
        url="https://asr.api.speechmatics.com/v2",
        auth_token=AUTH_TOKEN,
    )

    conf = {
        "type": "transcription",
        "transcription_config": {
            "language": LANGUAGE,
        },
    }

    # Save the uploaded file locally
    audio_filename = "uploaded_audio.mp3"
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

# Function to transcribe audio using Google Cloud Speech-to-Text API
def transcribe_with_google(audio_file, language_code):
    # Mapping language codes for different accents
    language_mapping = {
        "Australia": "en-AU",
        "American": "en-US",
        "British": "en-GB",
    }
    
    # Authenticate to Google Cloud Speech-to-Text
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/your/credentials.json"
    
    # Initialize Google Cloud Speech-to-Text client
    client = speech.SpeechClient()

    # Read the audio file content
    audio_content = audio_file.read()

    # Configure the recognition request
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(language_code=language_mapping[language_code])

    # Perform the transcription
    response = client.recognize(config=config, audio=audio)

    # Display the transcription results
    st.write("Transcribed Text (Google Cloud Speech-to-Text):")
    for result in response.results:
        st.write(result.alternatives[0].transcript)

# Main function to run the Streamlit app
def main():
    st.sidebar.title("Settings")
    st.sidebar.expander("Expand", expanded=True)
    service_option = st.sidebar.selectbox("Select Transcription Service", ("Speechmatics", "Google Cloud Speech-to-Text"), key="transcription_service")
    language_option = st.sidebar.radio("Select Language (Accent)", ("Australia", "American", "British"))

    st.title("Audio Transcription")
    st.header("Upload an Audio File")
    uploaded_file = st.file_uploader("", type=["mp3"])

    if uploaded_file is not None:
        st.header("Transcription Result")
        if st.button("Transcribe"):
            if service_option == "Speechmatics":
                transcribe_with_speechmatics(uploaded_file, language_option)
            elif service_option == "Google Cloud Speech-to-Text":
                transcribe_with_google(uploaded_file, language_option)

# Run the Streamlit app
if __name__ == "__main__":
    main()
