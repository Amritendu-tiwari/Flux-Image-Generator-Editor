import os
import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageOps
import io
import uuid

# Load API key
load_dotenv()
FLUX_API_KEY = os.getenv("FLUX_API_KEY")

BASE_URL = "https://api.bfl.ai/v1"
GEN_PATH = "/flux-pro-1.1-ultra"  # you can change to flux-dev or flux-pro

# ---- Helper Functions ----
def generate_image(prompt: str):
    """Generate image from text prompt using Flux API."""
    headers = {"x-key": FLUX_API_KEY, "accept": "application/json"}
    payload = {"prompt": prompt, "aspect_ratio": "1:1"}

    response = requests.post(f"{BASE_URL}{GEN_PATH}", json=payload, headers=headers)
    if not response.ok:
        return None, f"Error: {response.status_code} {response.text}"

    data = response.json()
    polling_url = data.get("polling_url")
    if not polling_url:
        return None, "No polling URL returned"

    # Poll until ready
    for _ in range(60):
        r2 = requests.get(polling_url, headers=headers).json()
        if r2.get("status") == "Ready":
            img_response = requests.get(r2["result"]["sample"])
            return Image.open(io.BytesIO(img_response.content)), None
    return None, "Timeout waiting for image"

def pencil_sketch(img: Image.Image):
    """Convert an image into pencil sketch grayscale."""
    return ImageOps.grayscale(img)

def resize_image(img: Image.Image, width: int, height: int):
    """Resize image to custom size."""
    return img.resize((width, height))

def upscale_image(img: Image.Image, scale: int):
    """Fake upscale by resizing (placeholder)."""
    w, h = img.size
    return img.resize((w * scale, h * scale))

def image_to_bytes(img: Image.Image, format="PNG"):
    """Convert PIL image to bytes for download."""
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

# ---- Streamlit UI ----
st.set_page_config(page_title="Flux Image Generator", layout="wide")

# Add custom CSS with Tailwind via CDN
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
<style>
body { background-color: #f9fafb; }
.stButton>button { 
    background-color: #3b82f6; 
    color: white; 
    padding: 8px 16px; 
    border-radius: 8px; 
    font-weight: 500;
    transition: background-color 0.3s; 
}
.stButton>button:hover { 
    background-color: #2563eb; 
}
.stTextArea textarea { 
    border-radius: 8px; 
    border: 1px solid #d1d5db; 
}
.stNumberInput input { 
    border-radius: 8px; 
    border: 1px solid #d1d5db; 
}
</style>
""", unsafe_allow_html=True)

st.title("🎨 Flux Image Generator & Editor")
st.markdown("Generate stunning images from text prompts or edit your uploaded images with ease.", unsafe_allow_html=True)

tabs = st.tabs(["✍️ Generate from Prompt", "🖼️ Upload & Edit"])

# --- Tab 1: Generate from Prompt ---
with tabs[0]:
    st.markdown('<div class="p-4 bg-white rounded-lg shadow-md">', unsafe_allow_html=True)
    st.subheader("Generate Image from Prompt")
    prompt = st.text_area("Enter a creative prompt", placeholder="e.g., A serene sunset over a mountain lake", height=100)

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Generate", key="generate_btn"):
            if not prompt:
                st.warning("Please enter a prompt.")
            else:
                with st.spinner("Generating image... This may take a moment."):
                    img, err = generate_image(prompt)
                    if err:
                        st.error(err)
                    else:
                        st.session_state['generated_image'] = img
                        st.session_state['generated_prompt'] = prompt

    if 'generated_image' in st.session_state:
        st.image(st.session_state['generated_image'], caption=f"Generated: {st.session_state['generated_prompt']}", width=512)
        img_bytes = image_to_bytes(st.session_state['generated_image'])
        st.download_button(
            label="Download Image",
            data=img_bytes,
            file_name=f"generated_image_{uuid.uuid4()}.png",
            mime="image/png",
            key="download_generated"
        )
    st.markdown('</div>', unsafe_allow_html=True)

# --- Tab 2: Upload & Edit ---
with tabs[1]:
    st.markdown('<div class="p-4 bg-white rounded-lg shadow-md">', unsafe_allow_html=True)
    st.subheader("Upload and Edit Image")
    uploaded = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"], help="Supports JPG, JPEG, and PNG formats")

    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="Original Image", width=512)
        st.session_state['uploaded_image'] = img

        st.markdown("### Edit Options")
        option = st.radio("Choose an operation:", [
            "Convert to Pencil Sketch",
            "Resize",
            "Upscale (2x or 3x)"
        ], horizontal=True)

        result = None
        if option == "Convert to Pencil Sketch":
            if st.button("Convert", key="sketch_btn"):
                result = pencil_sketch(img)
        elif option == "Resize":
            col_w, col_h = st.columns(2)
            with col_w:
                w = st.number_input("Width", value=512, step=50, min_value=50, max_value=2000)
            with col_h:
                h = st.number_input("Height", value=512, step=50, min_value=50, max_value=2000)
            if st.button("Resize", key="resize_btn"):
                result = resize_image(img, w, h)
        elif option == "Upscale (2x or 3x)":
            scale = st.selectbox("Scale factor", [2, 3], help="Choose 2x or 3x upscale")
            if st.button("Upscale", key="upscale_btn"):
                result = upscale_image(img, scale)

        if result:
            st.session_state['edited_image'] = result
            st.image(result, caption=f"Edited Image: {option}", width=512)
            img_bytes = image_to_bytes(result)
            st.download_button(
                label="Download Edited Image",
                data=img_bytes,
                file_name=f"edited_image_{uuid.uuid4()}.png",
                mime="image/png",
                key="download_edited"
            )
    st.markdown('</div>', unsafe_allow_html=True)