import streamlit as st
import os
import subprocess
from datetime import timedelta
try:
    import whisper
except ImportError:
    st.error("Please install whisper using: pip install git+https://github.com/openai/whisper.git")
    st.stop()

try:
    # Test if ffmpeg is available
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
except (subprocess.CalledProcessError, FileNotFoundError):
    st.error("""
        FFmpeg is not installed or not found in PATH. 
        Please install FFmpeg:
        1. Download from https://www.gyan.dev/ffmpeg/builds/
        2. Extract the zip file
        3. Add the bin folder to your system PATH
    """)
    st.stop()

import pysrt
from pysrt import SubRipItem
import tempfile
from pathlib import Path

def process_subtitles(input_path, language='hi'):
    """Process video and add subtitles"""
    # Create temp directory for output if it doesn't exist
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    # Define temporary file paths
    audio_path = str(temp_dir / "extracted_audio.mp3")
    srt_path = str(temp_dir / "subtitles.srt")
    output_path = str(temp_dir / "video_with_subtitles.mp4")
    
    try:
        # Step 1: Extract audio
        with st.spinner("Extracting audio from video..."):
            extract_audio(input_path, audio_path)
        
        # Step 2: Transcribe audio
        with st.spinner("Transcribing audio to English..."):
            segments = transcribe_audio_to_english_segments(audio_path, language)
        
        # Step 3: Create SRT file
        with st.spinner("Creating subtitles file..."):
            create_srt_file_from_segments(segments, srt_path)
        
        # Step 4: Add subtitles to video
        with st.spinner("Adding subtitles to video..."):
            add_subtitles_to_video(input_path, srt_path, output_path)
        
        return output_path, srt_path
        
    except Exception as e:
        # Cleanup temporary files
        for path in [audio_path, srt_path, output_path]:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except:
                pass
        raise e

def extract_audio(video_path, output_audio_path):
    """Extract audio from video file"""
    command = [
        'ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', output_audio_path,
        '-y'  # Overwrite output file if it exists
    ]
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode != 0:
        raise Exception(f"Error extracting audio: {process.stderr}")

def transcribe_audio_to_english_segments(audio_path, source_language, model_name='medium'):
    """Transcribe audio to English segments using Whisper"""
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, language=source_language, task='translate')
    return result['segments']

def format_timedelta_to_srt_time(td):
    """Convert timedelta to SRT time format"""
    total_seconds = int(td.total_seconds())
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def create_srt_file_from_segments(segments, output_srt_path):
    """Create SRT subtitle file from segments"""
    subs = pysrt.SubRipFile()
    
    for i, segment in enumerate(segments):
        start_time = timedelta(seconds=segment['start'])
        end_time = timedelta(seconds=segment['end'])
        text = segment['text'].strip()
        
        sub = SubRipItem(
            index=i + 1,
            start=format_timedelta_to_srt_time(start_time),
            end=format_timedelta_to_srt_time(end_time),
            text=text
        )
        subs.append(sub)
    
    subs.save(output_srt_path, encoding='utf-8')

def add_subtitles_to_video(video_path, srt_path, output_video_path):
    """Add subtitles to video file"""
    command = [
        'ffmpeg',
        '-i', video_path,
        '-vf', f"subtitles={srt_path}",
        '-c:v', 'libx264',
        '-c:a', 'copy',
        '-strict', '-2',
        output_video_path,
        '-y'  # Overwrite output file if it exists
    ]
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode != 0:
        raise Exception(f"Error adding subtitles: {process.stderr}")

def show_subtitle():
    st.title("Add Subtitles 🎤")
    
    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Add custom CSS for drag and drop
        st.markdown("""
            <style>
                .uploadedFile {
                    border: 2px dashed #1f77b4;
                    border-radius: 5px;
                    padding: 2rem;
                    text-align: center;
                }
                .uploadedFile:hover {
                    background-color: #f0f2f6;
                }
                .stButton button {
                    width: 100%;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Create a container for the uploader
        upload_container = st.container()
        
        with upload_container:
            uploaded_file = st.file_uploader(
                "Drag and drop or click to upload your video", 
                type=['mp4', 'mov', 'avi', 'mkv', 'webm'],
                help="Supported formats: MP4, MOV, AVI, MKV, WebM",
                accept_multiple_files=False,
                key="video_uploader"
            )
            
            # Show supported formats
            st.caption("Supported formats: MP4, MOV, AVI, MKV, WebM")
            
            # Show file details if uploaded
            if uploaded_file:
                file_details = {
                    "Filename": uploaded_file.name,
                    "File size": f"{uploaded_file.size / (1024*1024):.2f} MB",
                    "File type": uploaded_file.type
                }
                
                st.write("File Details:")
                for key, value in file_details.items():
                    st.text(f"{key}: {value}")
            
            # Add file size warning if necessary
            if uploaded_file and uploaded_file.size > 200 * 1024 * 1024:  # 200MB
                st.warning("⚠️ Large file detected! Processing might take longer.")
            
            # Add video format validation
            if uploaded_file:
                if uploaded_file.type not in ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm']:
                    st.error("⚠️ Please upload a supported video format.")
                    st.stop()
            
            if uploaded_file:
                # Show upload progress
                progress_text = "Uploading video..."
                progress_bar = st.progress(0)
                
                for i in range(100):
                    # Simulating upload progress
                    progress_bar.progress(i + 1)
                    if i == 99:
                        progress_text = "Upload complete!"
                progress_bar.empty()
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()
        
        try:
            # Show original video
            st.markdown("### Original Video")
            st.video(uploaded_file)
            
            with col2:
                st.markdown("### Subtitle Options")
                
                source_language = st.selectbox(
                    "Source Language",
                    ["hi", "en", "es", "fr", "de", "it", "ja", "ko", "zh"],
                    index=0,
                    format_func=lambda x: {
                        "hi": "Hindi",
                        "en": "English",
                        "es": "Spanish",
                        "fr": "French",
                        "de": "German",
                        "it": "Italian",
                        "ja": "Japanese",
                        "ko": "Korean",
                        "zh": "Chinese"
                    }[x],
                    help="Select the language of the video"
                )
                
                # Add a processing button
                process_button = st.button(
                    "Generate Subtitles",
                    help="Click to start generating English subtitles",
                    type="primary"
                )
            
            if process_button:
                try:
                    # Process the video
                    output_path, srt_path = process_subtitles(tfile.name, source_language)
                    
                    # Show success message
                    st.success("Subtitles generated successfully! 🎉")
                    
                    # Show video with subtitles
                    st.markdown("### Video with Subtitles")
                    with open(output_path, 'rb') as f:
                        st.video(f)
                    
                    # Add download buttons
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        with open(output_path, 'rb') as f:
                            st.download_button(
                                label="Download Video with Subtitles",
                                data=f.read(),
                                file_name="video_with_subtitles.mp4",
                                mime="video/mp4"
                            )
                    
                    with col4:
                        with open(srt_path, 'rb') as f:
                            st.download_button(
                                label="Download SRT File",
                                data=f.read(),
                                file_name="subtitles.srt",
                                mime="text/srt"
                            )
                    
                    # Cleanup temporary files
                    for path in [output_path, srt_path]:
                        try:
                            os.unlink(path)
                        except:
                            pass
                    
                except Exception as e:
                    st.error(f"An error occurred during processing: {str(e)}")
        
        finally:
            # Cleanup temporary input file
            try:
                os.unlink(tfile.name)
            except:
                pass
    
    else:
        # Show instructions when no file is uploaded
        st.markdown("""
        ### How to add subtitles to your video:
        1. Upload your video using the file uploader above
        2. Select the source language of the video
        3. Click the "Generate Subtitles" button to process your video
        4. Download the video with subtitles or the SRT file separately
        
        Features:
        - **Automatic Speech Recognition**: Uses OpenAI's Whisper model
        - **Language Translation**: Translates subtitles to English
        - **SRT Export**: Download subtitles in SRT format
        - **Multiple Language Support**: Works with various source languages
        """)
