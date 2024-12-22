import cv2
from moviepy import editor as mp
from moviepy.video.fx import fadein, fadeout
import streamlit as st
from transformers import pipeline
from PIL import Image
import os
import logging
import tempfile
import shutil  # Import shutil for directory removal

# Logger Setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("emotion_based_highlight_reel_creator.log")
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

def analyze_footage(video_path):
    """Analyze video footage to detect key moments with emotions."""
    logger.info("Analyzing video footage...")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    key_moments = []
    frame_count = 0

    try:
        emotion_detector = pipeline("image-classification", model="dima806/facial_emotions_image_detection")
    except Exception as e:
        logger.error("Error loading emotion detection model: %s", e)
        cap.release()
        return []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % int(fps * 1) == 0:  # Sample every 1 second
            try:
                resized_frame = cv2.resize(frame, (224, 224))
                rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                emotions = emotion_detector(pil_image)
                key_moments.append({
                    "frame": frame_count,
                    "emotions": emotions,
                    "image": rgb_frame
                })
            except Exception as e:
                logger.error("Error processing frame %s: %s", frame_count, e)

    cap.release()
    logger.info("Video footage analysis completed.")
    return key_moments

def generate_highlight_reel(video_path, key_moments, selected_emotions, output_path):
    """Generate a highlight reel based on user-selected emotions."""
    logger.info("Generating highlight reel...")
    try:
        clip = mp.VideoFileClip(video_path)
        fps = clip.fps

        # Collect highlight time intervals
        highlight_times = []
        for moment in key_moments:
            if any(selected_emo in [emo["label"] for emo in moment["emotions"]] for selected_emo in selected_emotions):
                start_time = max((moment["frame"] / fps) - 2.5, 0)  # Start 2.5 seconds before
                end_time = min((moment["frame"] / fps) + 2.5, clip.duration)  # End 2.5 seconds after
                highlight_times.append((start_time, end_time))

        # Merge overlapping time intervals
        merged_times = []
        for start, end in sorted(highlight_times):
            if merged_times and start <= merged_times[-1][1]:
                merged_times[-1] = (merged_times[-1][0], max(merged_times[-1][1], end))
            else:
                merged_times.append((start, end))

        # Create clips for each interval
        if not merged_times:
            logger.info("No highlights detected for the selected emotions.")
            return None

        highlight_clips = []
        for start, end in merged_times:
            # Ensure at least 5 seconds per highlight
            if end - start < 5:
                padding = (5 - (end - start)) / 2
                start = max(start - padding, 0)
                end = min(end + padding, clip.duration)
            highlight_clips.append(clip.subclip(start, end))

        # Concatenate all highlight clips
        final_highlight = mp.concatenate_videoclips(highlight_clips, method="compose")
        final_highlight.write_videofile(output_path, codec="libx264", audio_codec="aac")
        logger.info("Highlight reel saved at: %s", output_path)
        return output_path

    except Exception as e:
        logger.error("Error generating highlight reel: %s", e)
        return None

def show_emotion_based_highlight_reel():
    st.title("Emotion-Based Highlight Reel Creator 🎭")
    st.write("Upload multiple videos, detect emotions, and create a highlight reel based on selected emotions.")

    uploaded_files = st.file_uploader("Upload your videos", type=["mp4", "mov", "avi"], accept_multiple_files=True)
    if uploaded_files:
        temp_dir = tempfile.mkdtemp()
        video_paths = []

        for uploaded_file in uploaded_files:
            video_path = os.path.join(temp_dir, uploaded_file.name)
            with open(video_path, "wb") as f:
                f.write(uploaded_file.read())
            video_paths.append(video_path)

        for video_path in video_paths:
            st.video(video_path)

        st.write("### Step 1: Analyze Combined Videos for Emotions")

        def concatenate_videos(video_paths):
            """Concatenate multiple video files into a single video."""
            clips = [mp.VideoFileClip(path) for path in video_paths]
            return mp.concatenate_videoclips(clips, method="compose")

        concatenated_clip = concatenate_videos(video_paths)
        concatenated_path = os.path.join(temp_dir, "concatenated_video.mp4")
        concatenated_clip.write_videofile(concatenated_path, codec="libx264", audio_codec="aac")

        if st.button("Start Emotion Analysis"):
            st.write("Analyzing combined footage... Please wait.")
            placeholder = st.empty()

            if "key_moments" not in st.session_state:
                key_moments = analyze_footage(concatenated_path)
                st.session_state.key_moments = key_moments
            else:
                key_moments = st.session_state.key_moments

            if not key_moments:
                placeholder.write("No emotions detected. Please try with other videos.")
                return

            st.write("### Detected Frames with Emotions")
            for moment in key_moments:
                st.image(
                    moment["image"],
                    caption=f"Frame {moment['frame']} - {moment['emotions']}"
                )

        if "key_moments" in st.session_state:
            key_moments = st.session_state.key_moments
            st.write("### Step 2: Select Emotions for Highlight Reel")

            try:
                unique_emotions = set(
                    emo["label"] for moment in key_moments for emo in moment["emotions"]
                )
            except KeyError as e:
                logger.error("Error extracting emotions: %s", e)
                st.write("Error processing emotions. Please check the videos or try again.")
                return

            selected_emotions = st.multiselect("Select Emotions", options=list(unique_emotions))

            if st.button("Generate Highlight Reel"):
                if not selected_emotions:
                    st.write("Please select at least one emotion.")
                else:
                    st.write("Generating highlight reel... Please wait.")
                    placeholder = st.empty()

                    output_path = os.path.join(temp_dir, "highlight_reel.mp4")
                    result_path = generate_highlight_reel(concatenated_path, key_moments, selected_emotions, output_path)

                    if result_path:
                        placeholder.write("Highlight Reel Created!")
                        st.video(result_path)
                        with open(result_path, "rb") as f:
                            st.download_button("Download Highlight Reel", f, file_name="highlight_reel.mp4")
                    else:
                        placeholder.write("No scenes match your selected emotions. Try selecting different emotions or different videos.")

        # Cleanup temporary files
        for video_path in video_paths:
            os.remove(video_path)
        shutil.rmtree(temp_dir)  # Use shutil.rmtree to remove the directory and its contents
