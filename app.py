import streamlit as st
import sounddevice as sd
import soundfile as sf
import io
from google.cloud import speech
from google.cloud import texttospeech

# --- 1. Import your Backend Logic ---
# This assumes ing_assistant.py is in the same folder
try:
    from ing_assistant import get_bot_response, customers_df
except ImportError:
    st.error(
        "CRITICAL ERROR: 'ing_assistant.py' not found. Make sure it's in the same folder as app.py."
    )
    st.stop()
except Exception as e:
    st.error(f"Error importing ing_assistant: {e}")
    st.stop()


# --- 2. Configuration ---
# This app assumes you have set the GOOGLE_APPLICATION_CREDENTIALS
# environment variable in your terminal before running streamlit.

RECORD_DURATION = 10  # Duration of recording in seconds
SAMPLE_RATE = 16000  # Sample rate in Hz
CHANNELS = 1  # Mono audio

# --- 3. Google API Clients ---
try:
    speech_client = speech.SpeechClient()
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    st.error(f"Error initializing Google Cloud clients: {e}")
    st.error("Have you set the GOOGLE_APPLICATION_CREDENTIALS environment variable?")
    st.stop()


# --- 4. Speech-to-Text Function ---
def transcribe_audio(audio_data, language_code="en-US"):
    """
    Transcribes audio data using Google Cloud Speech-to-Text.
    """
    try:
        with io.BytesIO() as audio_file:
            sf.write(audio_file, audio_data, SAMPLE_RATE, format="WAV")
            content = audio_file.getvalue()

        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code=language_code,
        )

        response = speech_client.recognize(config=config, audio=audio)

        if not response.results:
            return "Could not understand audio."

        return response.results[0].alternatives[0].transcript
    except Exception as e:
        st.error(f"Speech-to-Text error: {e}")
        return ""


# --- 5. Text-to-Speech Function ---
def synthesize_speech(text, language_code="en-US"):
    """
    Synthesizes text into speech using Google Cloud Text-to-Speech.
    Returns the audio content as bytes.
    """
    try:
        input_text = texttospeech.SynthesisInput(text=text)

        voice_name_map = {
            "en-US": "en-US-Wavenet-F",
            "fr-FR": "fr-FR-Wavenet-B",
            "nl-BE": "nl-BE-Wavenet-A",
        }

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name_map.get(
                language_code, "en-US-Wavenet-F"
            ),  # Default to English
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = tts_client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )

        return response.audio_content
    except Exception as e:
        st.error(f"Text-to-Speech error: {e}")
        return None


# --- 6. Streamlit App UI ---
st.title("🤖 ING Voice Assistant (Leo)")

# Language selection in the sidebar
st.sidebar.title("Language")
language_options = {
    "English": "en-US",
    "Français": "fr-FR",
    "Nederlands": "nl-BE",
}
# Map to the simple codes your backend needs
language_map_simple = {
    "en-US": "en",
    "fr-FR": "fr",
    "nl-BE": "nl",
}

selected_language_name = st.sidebar.selectbox(
    "Select language:", options=language_options.keys()
)
selected_language_code_google = language_options[selected_language_name]
selected_language_code_backend = language_map_simple[selected_language_code_google]

st.write(
    f"Click the button to record 5 seconds of audio in **{selected_language_name}**."
)

# --- 7. Session State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "example_customer_id" not in st.session_state:
    st.session_state.example_customer_id = customers_df["customer_id"].iloc[0]

# --- MODIFIED: Display chat history ---
# This loop now runs first and displays the full history,
# including the "voice note" for the assistant.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and "audio" in message:
            st.audio(message["audio"], format="audio/mp3")

# --- 8. Main Record Button & Logic ---
if st.button("🔴 Record 5 Seconds"):
    with st.spinner(f"Recording for {RECORD_DURATION} seconds... Speak now!"):
        audio_data = sd.rec(
            int(RECORD_DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
        )
        sd.wait()
        st.success("Recording finished. Transcribing...")

        # 1. Transcribe audio to text
        user_text = transcribe_audio(audio_data, selected_language_code_google)
        if not user_text or user_text == "Could not understand audio.":
            st.error("Sorry, I couldn't understand that. Please try again.")
        else:
            # Add user message to state
            st.session_state.messages.append({"role": "user", "content": user_text})

            # 2. Generate bot response (THE INTEGRATION STEP)
            with st.spinner("Leo is thinking..."):
                bot_text = get_bot_response(
                    user_question=user_text,
                    customer_id=st.session_state.example_customer_id,
                    language=selected_language_code_backend,
                )

            # 3. Synthesize bot text to speech
            bot_audio = synthesize_speech(bot_text, selected_language_code_google)

            # --- MODIFIED: Add bot message with audio to state ---
            if bot_audio:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": bot_text,
                        "audio": bot_audio,  # Store the audio bytes
                    }
                )
            else:
                # Fallback if TTS fails
                st.session_state.messages.append(
                    {"role": "assistant", "content": bot_text}
                )

            # --- MODIFIED: Rerun the app ---
            # This will update the chat display (Section 7)
            # with the new messages we just added.
            st.rerun()
else:
    st.write("Click the button to start.")
