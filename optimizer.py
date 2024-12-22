import os
import subprocess
import streamlit as st
from typing import Tuple
import tempfile
import shutil

def optimize_video(input_path: str, output_path: str, resolution: Tuple[int, int], platform: str):
    """
    Optimizes a video for a specific platform by adjusting its resolution.
    """
    width, height = resolution

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Command to optimize video using ffmpeg
    command = [
        "ffmpeg",
        "-i", input_path,
        "-vf", f"scale={width}:{height}",
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        st.success(f"Video optimized for {platform} and saved to {output_path}")
    except subprocess.CalledProcessError as e:
        st.error(f"Error optimizing video: {e}")

def get_platform_resolution(platform: str) -> Tuple[int, int]:
    """
    Returns the recommended resolution for a specific platform.
    """
    resolutions = {
        "YouTube": (1920, 1080),  # Full HD
        "TikTok": (1080, 1920),   # Vertical video
        "Instagram": (1080, 1080) # Square video
    }

    return resolutions.get(platform, (1280, 720))  # Default to HD

def show_video_optimizer():
    st.title("Video Optimizer 📹")
    st.write("Optimize your video for different platforms like YouTube, TikTok, and Instagram.")

    uploaded_file = st.file_uploader("Upload your video", type=["mp4", "mov", "avi"])
    if uploaded_file:
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

        st.video(input_path)

        platform = st.selectbox("Select Platform", ["YouTube", "TikTok", "Instagram"])
        if st.button("Optimize Video"):
            resolution = get_platform_resolution(platform)
            output_path = os.path.join(temp_dir, f"{platform.lower()}_optimized.mp4")
            optimize_video(input_path, output_path, resolution, platform)

            st.write("### Optimized Video")
            with open(output_path, "rb") as f:
                st.video(f)

            with open(output_path, "rb") as f:
                st.download_button(
                    label="Download Optimized Video",
                    data=f.read(),
                    file_name=f"{platform.lower()}_optimized.mp4",
                    mime="video/mp4"
                )

        # Cleanup temporary files
        os.remove(input_path)
        shutil.rmtree(temp_dir) 