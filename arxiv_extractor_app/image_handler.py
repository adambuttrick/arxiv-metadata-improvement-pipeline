import os
import io
from pathlib import Path
from PIL import Image
import streamlit as st


class ImageHandler:

    def __init__(self):
        if 'current_image_array' not in st.session_state:
            st.session_state.current_image_array = None
        if 'current_image_path' not in st.session_state:
            st.session_state.current_image_path = None

    def cleanup_previous_image(self):
        if st.session_state.current_image_path and os.path.exists(st.session_state.current_image_path):
            try:
                os.remove(st.session_state.current_image_path)
                st.session_state.current_image_path = None
                st.session_state.current_image_array = None
            except Exception as e:
                st.warning(f"Error cleaning up previous image: {e}")

    def save_image(self, image, path):
        try:
            self.cleanup_previous_image()
            image.save(path)
            st.session_state.current_image_path = str(path)
            display_image = self.optimize_image(image)
            img_byte_arr = io.BytesIO()
            display_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            st.session_state.current_image_array = img_byte_arr

            return True
        except Exception as e:
            st.error(f"Error saving image: {e}")
            return False

    def optimize_image(self, image):
        try:
            max_width = 800
            ratio = max_width / image.size[0]
            new_size = (max_width, int(image.size[1] * ratio))
            optimized = image.resize(new_size, Image.Resampling.LANCZOS)
            return optimized
        except Exception as e:
            st.error(f"Error optimizing image: {e}")
            return image

    def get_current_image(self):
        return st.session_state.current_image_array

    def clear_state(self):
        self.cleanup_previous_image()
        st.session_state.current_image_array = None
        st.session_state.current_image_path = None
