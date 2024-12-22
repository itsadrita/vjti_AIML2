import os
import streamlit as st
import librosa
import numpy as np
from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Function to detect scenes
def detect_scenes(video_path, threshold=5.0):
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    return [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list]

# Function to determine if a scene is mostly silent
def is_scene_silent(audio_path, silence_threshold=-35.0):
    """
    Determines if a scene's audio is mostly silent based on the root mean square (RMS) energy.

    Parameters:
        audio_path (str): Path to the audio file extracted from the scene.
        silence_threshold (float): The threshold in decibels below which audio is considered silent. Default is -35 dB.

    Returns:
        bool: True if more than 90% of the audio is below the silence threshold, False otherwise.
    """
    y, sr = librosa.load(audio_path, sr=None)
    energy = librosa.feature.rms(y=y)[0]
    db_energy = librosa.amplitude_to_db(energy)
    silent_portion = np.sum(db_energy < silence_threshold) / len(db_energy)
    return silent_portion > 0.9  # 90% silence threshold

# Function to extract audio from a scene
def extract_audio(scene_clip, output_audio_path):
    if scene_clip.audio is not None:
        scene_clip.audio.write_audiofile(output_audio_path, codec="pcm_s16le", verbose=False, logger=None)

# Function to remove repeated files based on duration similarity
def remove_repeated_files(video_paths, min_duration=4.0):
    """
    Removes video files from the list if they are repetitive based on their content duration.

    Parameters:
        video_paths (list): List of paths to video files.
        min_duration (float): Minimum duration difference to consider a file unique.

    Returns:
        list: Filtered list of video paths.
    """
    filtered_paths = []
    previous_duration = None

    for video_path in video_paths:
        try:
            video_clip = VideoFileClip(video_path)
            current_duration = video_clip.duration
            video_clip.close()

            # Check if the video content repeats and remove if necessary
            if previous_duration is None or abs(current_duration - previous_duration) > min_duration:
                filtered_paths.append(video_path)

            previous_duration = current_duration

        except Exception as e:
            st.warning(f"Error processing file {video_path}: {e}")

    return filtered_paths

# Function to concatenate uploaded videos
def concatenate_videos(video_paths, output_path):
    clips = [VideoFileClip(video_path) for video_path in video_paths]
    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip.write_videofile(output_path, codec="libx264", fps=24)
    for clip in clips:
        clip.close()

# Main video processing function
def process_video(input_video_path, output_video_path, threshold, silence_threshold):
    scenes = detect_scenes(input_video_path, threshold=threshold)
    processed_clips = []

    video_clip = VideoFileClip(input_video_path)
    try:
        for i, (start_time, end_time) in enumerate(scenes):
            scene_clip = video_clip.subclip(start_time, end_time)
            scene_audio_path = f"temp_scene_{i+1}.wav"

            extract_audio(scene_clip, scene_audio_path)
            if os.path.exists(scene_audio_path) and not is_scene_silent(scene_audio_path, silence_threshold=silence_threshold):
                processed_clips.append(scene_clip)

            if os.path.exists(scene_audio_path):
                os.remove(scene_audio_path)

        if processed_clips:
            final_clip = concatenate_videoclips(processed_clips, method="compose")
            final_clip.write_videofile(output_video_path, codec="libx264", fps=24)
            final_clip.close()
        else:
            st.error("No relevant scenes found. No output video generated.")
    finally:
        video_clip.close()

# Streamlit UI
def show_sceneoptimizer():
    st.title("Video Scene Processor")

    st.markdown(
        """### Instructions:
        1. Upload multiple video files in the supported formats (e.g., MP4, AVI, MOV).
        2. Adjust the scene detection and silence threshold sliders as needed.
        3. Click "Process Videos" to concatenate the videos, detect scenes, and remove silent/repeated scenes.
        4. Download the processed video when it's ready.

        #### Parameters:
        - *Scene Detection Threshold*: Adjusts the sensitivity for detecting scene changes. Higher values detect fewer changes.
        - *Silence Threshold (dB)*: Defines the decibel level below which audio is considered silent. A lower value detects more silence.
        """
    )

    uploaded_files = st.file_uploader("Upload Video Files", type=["mp4", "avi", "mov"], accept_multiple_files=True)

    if uploaded_files:
        threshold = st.slider("Scene Detection Threshold", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
        silence_threshold = st.slider("Silence Threshold (dB)", min_value=-60.0, max_value=0.0, value=-35.0, step=1.0)

        if st.button("Process Videos"):
            with st.spinner("Processing videos..."):
                video_paths = []

                # Save uploaded videos to disk
                for uploaded_file in uploaded_files:
                    video_path = f"input_{uploaded_file.name}"
                    with open(video_path, "wb") as f:
                        f.write(uploaded_file.read())
                    video_paths.append(video_path)

                # Remove repetitive video files based on duration
                filtered_video_paths = remove_repeated_files(video_paths, min_duration=4.0)

                concatenated_video_path = "concatenated_video.mp4"
                output_video_path = "processed_video.mp4"

                try:
                    # Concatenate videos
                    concatenate_videos(filtered_video_paths, concatenated_video_path)

                    # Process the concatenated video
                    process_video(concatenated_video_path, output_video_path, threshold, silence_threshold)

                    # Display the processed video
                    st.success("Processing complete! Download your video below.")
                    st.video(output_video_path)
                finally:
                    # Clean up temporary files
                    for video_path in video_paths:
                        try:
                            os.remove(video_path)
                        except FileNotFoundError:
                            st.warning(f"Temporary file {video_path} not found for deletion.")
                    try:
                        os.remove(concatenated_video_path)
                    except (FileNotFoundError, PermissionError):
                        st.warning(
                            f"Could not remove the concatenated video file {concatenated_video_path}. Ensure it's not in use."
                        )

if __name__ == "__main__":
    main()