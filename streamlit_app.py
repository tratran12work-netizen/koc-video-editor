import PIL.Image
# Vá lỗi tương thích phiên bản Pillow mới để không bị sập khi render video
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import tempfile
import os
import streamlit as st
from moviepy import editor as mp

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="KOC Video Editor", layout="centered")
st.title("🎬 KOC Video Generator Pro")
st.markdown("Công cụ cắt ghép video tự động dành cho Marketing")

# --- HÀM XỬ LÝ VIDEO ---
def process_video(video_a_path, video_b_paths, text_content, text_style):
    try:
        # 1. Xử lý Video A (Lấy Audio)
        clip_a = mp.VideoFileClip(video_a_path)
        
        # Tự động cắt theo thanh trượt slider nếu có thiết lập trim
        if 'trim_start' in st.session_state and 'trim_end' in st.session_state:
            trim_start = st.session_state.trim_start
            trim_end = st.session_state.trim_end
            if trim_start > 0 or trim_end < clip_a.duration:
                clip_a = clip_a.subclip(trim_start, trim_end)
        
        audio_a = clip_a.audio
        
        # 2. Xử lý Video B (Cắt các đoạn 10-15s mỗi clip để trộn ghép)
        b_clips = []
        for path in video_b_paths:
            clip = mp.VideoFileClip(path)
            # Lấy tối đa 15s đầu hoặc toàn bộ nếu clip ngắn hơn 15s
            duration = min(15, clip.duration)
            b_clips.append(clip.subclip(0, duration))
            
        # Trộn hoặc nối các clip B lại với nhau (tùy thuộc vào logic xử lý của bạn)
        # Ở đây dùng tạm cấu trúc nền cơ bản để đảm bảo nhận diện hết biến 'mp'
        if b_clips:
            final_video = mp.concatenate_videoclips(b_clips, method="compose")
            final_video = final_video.set_audio(audio_a)
            
            # Khởi tạo TextClip nếu có nội dung chèn chữ
            if text_content:
                # Cấu hình chữ cơ bản để lách lỗi hệ thống font nền
                txt_clip = mp.TextClip(text_content, fontsize=24, color='white', font='Montserrat')
                txt_clip = txt_clip.set_pos('center').set_duration(final_video.duration)
                final_video = mp.CompositeVideoClip([final_video, txt_clip])
                
            return final_video
            
    except Exception as e:
        st.error(f"Có lỗi xảy ra trong quá trình render: {str(e)}")
        return None