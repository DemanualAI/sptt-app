import streamlit as st
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from google.cloud import speech
import os
import time
import openai

# Function to transcribe audio using Speechmatics API
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

# Main function to run the Streamlit app
def main():
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

    st.title("Audio Transcription")
    st.header("Upload an Audio File")
    uploaded_file = st.file_uploader("")

    if uploaded_file is not None:
        st.header("Transcription Result")
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


# Run the Streamlit app
if __name__ == "__main__":
    main()

