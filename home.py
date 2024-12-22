import streamlit as st

def show_home():
    st.title("Welcome to VidAI 🎬")
    
    st.markdown("""
    ### AI-Powered Video Editing Made Simple
    
    Choose from our powerful features:
    
    * 🎯 **Trim Video** - Cut and trim your videos with precision
    * ✨ **Enhance Video** - Improve video quality using AI
    * 🎥 **Highlight Reel** - Automatically generate highlight clips
    * 🎥 **Highlight Extractor** - Extract highlights from your videos
    * 🎥 **Scene Optimizer** - Optimize your scenes for better video quality
    * 🎥 **Emotion Processor** - Process your videos for better video quality
    * 🎥 **Transitions** - Add transitions to your videos
    * 🎥 **Emotion-Based Highlight Reel** - Generate highlight reels based on emotions
    
    Get started by selecting a feature from the sidebar!
    """)
    
    # Sample video or demo
    st.markdown("### How it works")
    st.video("https://www.youtube.com/watch?v=lQ4S_tbYygk&pp=ygUXdW5mb3J0dW5hdGVseSBmb3J0dW5hdGU%3D")
