import cv2
import os
import numpy as np
import streamlit as st
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import tempfile
import shutil

def extract_highlight(video_path, highlight_duration):
    """
    Extracts the most interesting part of the video based on audio intensity and scene changes.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"The file '{video_path}' does not exist.")

    try:
        video = VideoFileClip(video_path)
    except Exception as e:
        raise ValueError(f"Could not process video file: {e}")

    # Adjust highlight duration if video is too short
    if video.duration < highlight_duration:
        st.warning(f"Requested highlight duration ({highlight_duration}s) exceeds video duration ({video.duration}s).")
        highlight_duration = video.duration
        st.warning(f"Highlight duration adjusted to {highlight_duration:.2f} seconds.")

    # Extract audio and analyze nonsilent parts
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
        audio_path = temp_audio_file.name
        video.audio.write_audiofile(audio_path)

    audio = AudioSegment.from_file(audio_path, format="wav")
    silence_thresh = audio.dBFS - 10  # Dynamic silence threshold
    nonsilent_ranges = detect_nonsilent(audio, min_silence_len=300, silence_thresh=silence_thresh)

    if not nonsilent_ranges:
        os.remove(audio_path)
        raise ValueError("No significant audio activity detected in the video.")

    fps = int(video.fps)
    total_frames = int(video.duration * fps)
    nonsilent_ranges_frames = [(int(start / 1000 * fps), int(end / 1000 * fps)) for start, end in nonsilent_ranges]

    # Analyze scene changes
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        os.remove(audio_path)
        raise ValueError(f"Unable to open video file: {video_path}")

    frame_diffs = []
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            diff = cv2.absdiff(gray_frame, prev_frame)
            frame_diffs.append(np.sum(diff))
        prev_frame = gray_frame

    cap.release()
    frame_diffs = frame_diffs[:total_frames]

    if not frame_diffs:
        os.remove(audio_path)
        raise ValueError("No significant scene changes detected in the video.")

    # Combine scores
    frame_scores = np.zeros(total_frames)
    for start, end in nonsilent_ranges_frames:
        frame_scores[start:end] += 1

    for i, diff in enumerate(frame_diffs):
        if i < len(frame_scores):  # Ensure index is within bounds
            frame_scores[i] += diff

    # Adjust highlight duration
    highlight_frames = int(highlight_duration * fps)
    if len(frame_scores) < highlight_frames:
        highlight_duration = len(frame_scores) / fps
        st.warning(f"Highlight duration adjusted to {highlight_duration:.2f} seconds.")

    highlight_frames = int(highlight_duration * fps)
    start_frame = np.argmax(
        [np.sum(frame_scores[i:i + highlight_frames]) for i in range(len(frame_scores) - highlight_frames)]
    )
    end_frame = start_frame + highlight_frames

    # Extract and save the highlight
    output_path = os.path.join(tempfile.gettempdir(), "highlight.mp4")
    try:
        highlight_clip = video.subclip(start_frame / fps, end_frame / fps)
        highlight_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    finally:
        os.remove(audio_path)  # Clean up temporary file

    return output_path

def show_highlight_extractor():
    st.title("Highlight Extractor 🎬")
    st.write("Upload a video to extract the most interesting highlights based on audio intensity and scene changes.")

    uploaded_file = st.file_uploader("Upload your video", type=["mp4", "avi"])
    if uploaded_file:
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, uploaded_file.name)
        with open(video_path, "wb") as f:
            f.write(uploaded_file.read())

        st.video(video_path)

        highlight_duration = st.number_input("Enter the desired highlight duration in seconds", min_value=1, value=10)

        if st.button("Extract Highlight"):
            try:
                output_path = extract_highlight(video_path, highlight_duration)
                st.success("Highlight extraction completed successfully.")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button("Download Highlight", f, file_name="highlight.mp4")
            except Exception as e:
                st.error(f"Error: {e}")

        shutil.rmtree(temp_dir) 