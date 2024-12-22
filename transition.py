import streamlit as st
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx
import tempfile
import os
import logging

logging.basicConfig(level=logging.INFO)

def show_transition(clip1, clip2, transition, duration):
    """Apply a specified transition between two clips."""
    if transition == "crossfade":
        return [clip1.crossfadeout(duration), clip2.crossfadein(duration)]
    elif transition == "fade":
        return [clip1.fadeout(duration), clip2.fadein(duration)]
    elif transition == "mirrorx":
        return [clip1, clip2.fx(vfx.mirror_x)]
    elif transition == "mirrory":
        return [clip1, clip2.fx(vfx.mirror_y)]
    elif transition == "blackwhite":
        return [clip1, clip2.fx(vfx.blackwhite)]
    elif transition == "blur":
        return [clip1, clip2.fx(vfx.blur, size=10)]
    elif transition == "zoom_in":
        return [clip1, clip2.fx(vfx.resize, newsize=(clip2.w * 1.2, clip2.h * 1.2))]
    elif transition == "zoom_out":
        return [clip1, clip2.fx(vfx.resize, newsize=(clip2.w * 0.8, clip2.h * 0.8))]
    elif transition == "invert_colors":
        return [clip1, clip2.fx(vfx.invert_colors)]
    elif transition == "brightness":
        return [clip1, clip2.fx(vfx.colorx, 1.5)]
    else:
        return [clip1, clip2]

st.title("Video Processor with Transitions")
st.write("Upload multiple videos, add transitions, and process them into a final output.")

uploaded_files = st.file_uploader("Upload video files", type=["mp4", "avi", "mov"], accept_multiple_files=True)
if uploaded_files:
    temp_dir = tempfile.mkdtemp()
    video_clips = []

    for uploaded_file in uploaded_files:
        input_path = os.path.join(temp_dir, uploaded_file.name)

        # Save each uploaded file to the temporary directory
        with open(input_path, "wb") as f:
            f.write(uploaded_file.read())

        video = VideoFileClip(input_path)
        video_clips.append(video)

    st.write(f"Number of videos uploaded: {len(video_clips)}")

    if len(video_clips) > 1:
        st.write("Preview concatenated video below:")
        preview_video = concatenate_videoclips(video_clips, method="compose")
        preview_path = os.path.join(temp_dir, "preview_video.mp4")
        preview_video.write_videofile(preview_path, codec="libx264", fps=24, audio_codec="aac")

        with open(preview_path, "rb") as f:
            st.video(f.read())

        segments = st.text_input("Enter segment times for final processing (comma-separated, e.g., 0,5,10)")
        transitions = st.text_input("Enter transitions (comma-separated, e.g., crossfade,fade)")

        if st.button("Process Final Video"):
            try:
                output_path = os.path.join(temp_dir, "final_video.mp4")

                # Parse segments and transitions
                segment_times = [float(t) for t in segments.split(",")]
                transition_types = transitions.split(",")

                if len(transition_types) != len(segment_times) - 2:
                    st.error("Number of transitions must match the number of cuts between segments.")
                    raise ValueError("Invalid transition input.")

                # Create subclips based on segment times
                clips = [preview_video.subclip(segment_times[i], segment_times[i + 1]) for i in range(len(segment_times) - 1)]

                # Add transitions
                final_clips = []
                for i in range(len(clips) - 1):
                    clip1, clip2 = clips[i], clips[i + 1]
                    transitioned_clips = apply_transition(clip1, clip2, transition_types[i], duration=1.0)
                    final_clips.append(transitioned_clips[0])
                    final_clips.append(transitioned_clips[1])

                final_clips.append(clips[-1])  # Add the last clip without transition

                # Concatenate all clips
                final_video = concatenate_videoclips(final_clips, method="compose")
                final_video.write_videofile(output_path, codec="libx264", fps=24, audio_codec="aac")

                st.success("Final video processed successfully!")

                # Display the final video in the app
                with open(output_path, "rb") as f:
                    st.video(f.read())

                # Optionally allow the user to download the final video
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="Download Final Video",
                        data=f,
                        file_name="final_video.mp4",
                        mime="video/mp4",
                    )

            except Exception as e:
                st.error(f"Error processing final video: {str(e)}")

            finally:
                # Cleanup temporary files
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        for file in os.listdir(temp_dir):
                            os.remove(os.path.join(temp_dir, file))
                        os.rmdir(temp_dir)
                    except Exception as cleanup_error:
                        logging.warning(f"Error during cleanup: {cleanup_error}")

    else:
        st.warning("Please upload more than one video to process transitions.")

    # Close video files
    for video in video_clips:
        video.close()