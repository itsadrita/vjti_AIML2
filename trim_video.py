import streamlit as st
from moviepy.editor import VideoFileClip
import tempfile
import os

def show_trim_video():
    st.title("Trim Video ✂️")
    
    uploaded_file = st.file_uploader("Upload your video", type=['mp4', 'mov', 'avi'])
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        tfile.close()  # Close the file to ensure it's not being used
        
        # Load video
        video = VideoFileClip(tfile.name)
        duration = video.duration
        
        st.video(uploaded_file)
        
        # Trim controls
        st.markdown("### Trim Settings")
        start_time = st.slider("Start Time (seconds)", 0, int(duration), 0)
        end_time = st.slider("End Time (seconds)", 0, int(duration), int(duration))
        
        if st.button("Trim Video"):
            if start_time < end_time:
                trimmed = video.subclip(start_time, end_time)
                
                # Save trimmed video
                output_path = "temp_trimmed.mp4"
                trimmed.write_videofile(output_path)
                
                st.success("Video trimmed successfully!")
                st.video(output_path)
                
                # Add download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="Download Trimmed Video",
                        data=f,
                        file_name="trimmed_video.mp4",
                        mime="video/mp4"
                    )
                
                # Cleanup
                video.close()
                trimmed.close()
                os.unlink(tfile.name)
                os.remove(output_path)
                
            else:
                st.error("End time must be greater than start time!")
