import cv2
from diffusers import StableDiffusionPipeline
from PIL import Image
import torch
import streamlit as st
from fer import FER
import numpy as np
import pygame
import os
import tempfile
import shutil
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip
from scipy.io import wavfile
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Initialize Spotify client
client_credentials_manager = SpotifyClientCredentials(
    client_id='647d6d6fd0af403bbeb245171f80505f',
    client_secret='97d22dd241984ea48eb2ab65067180fc'
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def detect_emotion_from_image(img):
    try:
        if isinstance(img, Image.Image):
            img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        detector = FER(mtcnn=True)
        result = detector.detect_emotions(img)
        if result and len(result) > 0:
            emotions = result[0]['emotions']
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
            return dominant_emotion
        return "neutral"
    except Exception as e:
        st.error(f"Error detecting emotion: {e}")
        return "neutral"

def detect_emotion_from_video(video_path):
    cap = cv2.VideoCapture(video_path)
    emotions = []
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % 10 == 0:
            try:
                emotion = detect_emotion_from_image(frame)
                emotions.append(emotion)
            except Exception as e:
                st.error(f"Error processing frame {frame_count}: {e}")
        frame_count += 1
    cap.release()
    if emotions:
        return max(set(emotions), key=emotions.count)
    return "neutral"

def generate_background(emotion):
    model_id = "runwayml/stable-diffusion-v1-5"
    pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float32)
    pipe = pipe.to("cpu")
    emotion_prompts = {
        "happy": "a bright sunny day in a beautiful garden with blooming flowers, cheerful atmosphere",
        "sad": "a rainy day with gray clouds, melancholic atmosphere, gentle rain falling",
        "angry": "dramatic stormy sky with dark clouds and lightning, intense atmosphere",
        "fear": "dark misty forest with fog, mysterious atmosphere",
        "surprise": "magical starry night sky with aurora borealis, wonderful atmosphere",
        "neutral": "calm serene landscape with soft clouds, peaceful atmosphere",
        "disgust": "abstract dark pattern with moody lighting",
    }
    prompt = emotion_prompts.get(emotion.lower(), "beautiful landscape with natural lighting")
    with torch.no_grad():
        image = pipe(prompt, num_inference_steps=20).images[0]
    return image

def generate_music(emotion, duration=5):
    try:
        pygame.mixer.init(frequency=44100)
        sample_rate = 44100
        def generate_tone(frequency, duration, volume=0.5):
            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = np.sin(2 * np.pi * frequency * t)
            return (tone * volume * 32767).astype(np.int16)
        def save_temp_music(audio_data, filename="temp_music.wav"):
            wavfile.write(filename, sample_rate, audio_data)
            return filename
        emotion_music = {
            "happy": {"frequencies": [392, 440, 494, 523], "rhythm": 0.2, "volume": 0.6},
            "sad": {"frequencies": [440, 415, 392, 370], "rhythm": 0.4, "volume": 0.4},
            "angry": {"frequencies": [277, 311, 370, 415], "rhythm": 0.15, "volume": 0.7},
            "fear": {"frequencies": [233, 277, 311, 370], "rhythm": 0.3, "volume": 0.5},
            "surprise": {"frequencies": [523, 587, 659, 698], "rhythm": 0.25, "volume": 0.6},
            "neutral": {"frequencies": [349, 392, 440, 494], "rhythm": 0.3, "volume": 0.5},
            "disgust": {"frequencies": [466, 415, 392, 370], "rhythm": 0.2, "volume": 0.5}
        }
        params = emotion_music.get(emotion.lower(), emotion_music["neutral"])
        music_data = np.array([], dtype=np.int16)
        for _ in range(int(duration / params["rhythm"])):
            freq = np.random.choice(params["frequencies"])
            tone = generate_tone(freq, params["rhythm"], params["volume"])
            music_data = np.concatenate([music_data, tone])
        timestamp = int(time.time())
        temp_file = f"temp_music_{timestamp}.wav"
        save_temp_music(music_data, temp_file)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        return temp_file
    except Exception as e:
        st.error(f"Error generating music: {e}")
        return None

def get_spotify_recommendations(emotion):
    try:
        emotion_params = {
            "happy": {"seed_genres": ["pop", "dance", "disco"], "target_valence": 0.8, "target_energy": 0.8, "limit": 5},
            "sad": {"seed_genres": ["classical", "piano", "indie"], "target_valence": 0.2, "target_energy": 0.3, "limit": 5},
            "angry": {"seed_genres": ["metal", "rock", "punk"], "target_valence": 0.3, "target_energy": 0.9, "limit": 5},
            "fear": {"seed_genres": ["ambient", "classical", "instrumental"], "target_valence": 0.3, "target_energy": 0.4, "limit": 5},
            "surprise": {"seed_genres": ["electronic", "dance", "pop"], "target_valence": 0.7, "target_energy": 0.7, "limit": 5},
            "neutral": {"seed_genres": ["indie", "alternative", "folk"], "target_valence": 0.5, "target_energy": 0.5, "limit": 5},
            "disgust": {"seed_genres": ["industrial", "electronic", "rock"], "target_valence": 0.3, "target_energy": 0.6, "limit": 5}
        }
        params = emotion_params.get(emotion.lower(), emotion_params["neutral"])
        seed_genres = ",".join(params["seed_genres"])
        recommendations = sp.recommendations(
            seed_genres=seed_genres,
            target_valence=params["target_valence"],
            target_energy=params["target_energy"],
            limit=params["limit"]
        )
        songs = []
        for track in recommendations['tracks']:
            artists = ", ".join([artist['name'] for artist in track['artists']])
            song_info = f"{track['name']} - {artists}"
            song_url = track['external_urls']['spotify']
            songs.append({'name': song_info, 'url': song_url})
        return songs
    except Exception as e:
        st.error(f"Error getting Spotify recommendations: {e}")
        return []

def create_audiovisual_experience(background_path, audio_path, emotion):
    try:
        video_clip = ImageClip(background_path)
        audio_clip = AudioFileClip(audio_path)
        video_clip = video_clip.set_duration(audio_clip.duration)
        final_clip = video_clip.set_audio(audio_clip)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"emotion_experience_{emotion}_{timestamp}.mp4"
        final_clip.write_videofile(output_path, fps=24)
        video_clip.close()
        audio_clip.close()
        return output_path
    except Exception as e:
        st.error(f"Error creating audiovisual experience: {e}")
        return None

def process_media(media_path):
    music_file = None
    background_path = None
    final_output = None
    try:
        is_video = media_path.lower().endswith(('.mp4', '.avi'))
        if is_video:
            emotion = detect_emotion_from_video(media_path)
        else:
            img = Image.open(media_path)
            emotion = detect_emotion_from_image(img)
        st.write(f"Detected emotion: {emotion}")
        music_file = generate_music(emotion)
        if music_file:
            st.write("Playing generated music...")
        songs = get_spotify_recommendations(emotion)
        st.write("Spotify Recommendations for your mood:")
        for song in songs:
            st.write(f"🎵 {song['name']}")
            st.write(f"   Listen here: {song['url']}")
        background = generate_background(emotion)
        if background is None:
            st.error("Failed to generate background. Please check your API key and connection.")
            return emotion, None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        background_path = f"generated_background_{emotion}_{timestamp}.png"
        background.save(background_path, format="PNG")
        st.write(f"Background saved as: {background_path}")
        if music_file and background_path:
            st.write("Creating audiovisual experience...")
            final_output = create_audiovisual_experience(background_path, music_file, emotion)
            if final_output:
                st.write(f"Created audiovisual experience: {final_output}")
        if music_file and os.path.exists(music_file):
            try:
                pygame.mixer.music.stop()
                os.remove(music_file)
            except Exception as e:
                st.error(f"Error cleaning up music file: {e}")
        if background_path and os.path.exists(background_path):
            try:
                os.remove(background_path)
            except Exception as e:
                st.error(f"Error cleaning up background file: {e}")
        return emotion, final_output
    except Exception as e:
        st.error(f"Error processing media: {e}")
        for file_path in [music_file, background_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        return None, None

def show_emotion_processor():
    st.title("Emotion-Based Media Processor 🎭")
    st.write("Upload an image or video to detect emotions and create an audiovisual experience.")
    uploaded_file = st.file_uploader("Upload your media file", type=["png", "jpg", "jpeg", "mp4", "avi"])
    if uploaded_file:
        temp_dir = tempfile.mkdtemp()
        media_path = os.path.join(temp_dir, uploaded_file.name)
        with open(media_path, "wb") as f:
            f.write(uploaded_file.read())
        st.video(media_path) if media_path.lower().endswith(('.mp4', '.avi')) else st.image(media_path)
        if st.button("Process Media"):
            emotion, output_path = process_media(media_path)
            if emotion and output_path:
                st.success(f"Processing complete! Detected emotion: {emotion}")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button("Download Audiovisual Experience", f, file_name=output_path)
        shutil.rmtree(temp_dir) 