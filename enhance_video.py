import streamlit as st
import cv2
import numpy as np
import tempfile
import os
from pathlib import Path

def process_video(input_path, enhancement_options):
    """Process video with selected enhancement options"""
    # Create temp directory for output if it doesn't exist
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    output_path = str(temp_dir / "enhanced_video.mp4")
    
    # Open the input video
    vidcap = cv2.VideoCapture(input_path)
    
    if not vidcap.isOpened():
        raise ValueError(f"Could not open video at path: {input_path}")
    
    # Get video properties
    frame_width = int(vidcap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    total_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Initialize enhancement parameters based on user selection
    upscale_factor = 2 if "Super Resolution" in enhancement_options else 1
    apply_sharpening = "Sharpening" in enhancement_options
    
    try:
        # Try different codecs in order of preference
        codecs = [
            ('mp4v', '.mp4'),
            ('XVID', '.avi'),
            ('MJPG', '.avi'),
            ('DIVX', '.avi')
        ]
        
        out = None
        for codec, ext in codecs:
            try:
                output_path = str(temp_dir / f"enhanced_video{ext}")
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(
                    output_path,
                    fourcc,
                    fps,
                    (frame_width * upscale_factor, frame_height * upscale_factor)
                )
                if out.isOpened():
                    break
            except:
                if out is not None:
                    out.release()
                continue
        
        if out is None or not out.isOpened():
            raise ValueError("Could not initialize any video codec")

        # Define sharpening kernel
        sharpening_kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Process each frame
        frame_count = 0
        while True:
            success, frame = vidcap.read()
            if not success:
                break
                
            # Update progress
            progress = int((frame_count / total_frames) * 100)
            progress_bar.progress(progress)
            status_text.text(f"Processing frame {frame_count}/{total_frames}")
            
            # Apply enhancements
            processed_frame = frame.copy()  # Make a copy to avoid modifying the original
            
            if "Super Resolution" in enhancement_options:
                processed_frame = cv2.resize(
                    processed_frame, 
                    (frame_width * upscale_factor, frame_height * upscale_factor), 
                    interpolation=cv2.INTER_CUBIC
                )
                
            if apply_sharpening:
                processed_frame = cv2.filter2D(processed_frame, -1, sharpening_kernel)
                
            if "Brightness" in enhancement_options:
                processed_frame = cv2.convertScaleAbs(processed_frame, alpha=1.2, beta=10)
                
            if "Contrast" in enhancement_options:
                processed_frame = cv2.convertScaleAbs(processed_frame, alpha=1.3, beta=0)
                
            # Write the enhanced frame
            out.write(processed_frame)
            frame_count += 1
        
        # Release resources
        vidcap.release()
        out.release()
        
        # Clear progress bar and status
        progress_bar.empty()
        status_text.empty()
        
        return output_path
        
    except Exception as e:
        # Clean up resources in case of error
        vidcap.release()
        if 'out' in locals() and out is not None:
            out.release()
        raise e

def show_enhance_video():
    st.title("Enhance Video 🎨")
    
    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload your video", 
            type=['mp4', 'mov', 'avi'],
            help="Upload a video file to enhance"
        )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()  # Close the file immediately after writing
        
        try:
            # Show original video
            st.markdown("### Original Video")
            st.video(uploaded_file)
            
            with col2:
                st.markdown("### Enhancement Options")
                
                enhance_options = st.multiselect(
                    "Select enhancement options",
                    [
                        "Super Resolution",
                        "Sharpening",
                        "Brightness",
                        "Contrast"
                    ],
                    default=["Super Resolution", "Sharpening"],
                    help="Choose the enhancements to apply to your video"
                )
                
                # Add a processing button with custom styling
                process_button = st.button(
                    "Enhance Video",
                    help="Click to start processing the video with selected enhancements",
                    type="primary"
                )
            
            if process_button and enhance_options:
                try:
                    with st.spinner("Processing video... This may take a while."):
                        # Process the video
                        output_path = process_video(tfile.name, enhance_options)
                        
                        # Show success message
                        st.success("Video enhanced successfully! 🎉")
                        
                        # Show enhanced video
                        st.markdown("### Enhanced Video")
                        with open(output_path, 'rb') as f:
                            st.video(f)
                        
                        # Add download button
                        with open(output_path, 'rb') as f:
                            st.download_button(
                                label="Download Enhanced Video",
                                data=f.read(),
                                file_name="enhanced_video.mp4",
                                mime="video/mp4"
                            )
                        
                        # Cleanup enhanced video file
                        try:
                            os.unlink(output_path)
                        except:
                            pass  # Ignore if file is still in use
                    
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")
        
        finally:
            # Cleanup temporary input file
            try:
                os.unlink(tfile.name)
            except:
                pass  # Ignore if file is still in use
    
    else:
        # Show instructions when no file is uploaded
        st.markdown("""
        ### How to enhance your video:
        1. Upload your video using the file uploader above
        2. Select the enhancement options you want to apply
        3. Click the "Enhance Video" button to process your video
        4. Download the enhanced video when processing is complete
        
        Available enhancements:
        - **Super Resolution**: Increase video resolution
        - **Sharpening**: Enhance video sharpness and details
        - **Brightness**: Adjust video brightness
        - **Contrast**: Improve video contrast
        """)
