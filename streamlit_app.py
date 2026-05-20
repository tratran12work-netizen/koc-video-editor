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

# --- 1. GIAO DIỆN TẢI VIDEO SOURCE (INPUT) ---
st.header("1. Tải Video Source")

# Ô tải Video A
video_a_file = st.file_uploader("Video A (Lấy Audio)", type=["mp4", "mov", "mpeg4"])

if video_a_file:
    st.info(f"Đã tải xong Video A")
    # Thanh trượt cắt video A
    st.session_state.trim_start, st.session_state.trim_end = st.slider(
        "Chọn đoạn muốn giữ lại (giây)", 
        0.0, 60.0, (0.0, 15.0)
    )

# Ô tải nhiều Video B cùng lúc
video_b_files = st.file_uploader("Video B (Tối đa 10 clip lấy hình)", type=["mp4", "mov", "mpeg4"], accept_multiple_files=True)

# --- 2. CÀI ĐẶT TEXT CHÈN LÊN VIDEO ---
st.header("2. Cài đặt Text")
text_content = st.text_area("Nhập nội dung Text chèn lên video", placeholder="Mẫu nội dung KOC...")
text_style = st.selectbox("Chọn Style Text (Font Montserrat)", ["Chữ Trắng - Viền Xanh", "Chữ Vàng - Viền Đen"])

# --- HÀM XỬ LÝ VIDEO NGẦM ---
def process_video(video_a_path, video_b_paths, text_content, text_style):
    try:
        # Xử lý Video A (Lấy Audio)
        clip_a = mp.VideoFileClip(video_a_path)
        if 'trim_start' in st.session_state and 'trim_end' in st.session_state:
            trim_start = st.session_state.trim_start
            trim_end = st.session_state.trim_end
            if trim_start > 0 or trim_end < clip_a.duration:
                clip_a = clip_a.subclip(trim_start, min(trim_end, clip_a.duration))
        audio_a = clip_a.audio
        
        # Xử lý Video B
        b_clips = []
        for path in video_b_paths:
            clip = mp.VideoFileClip(path)
            duration = min(15, clip.duration)
            b_clips.append(clip.subclip(0, duration))
            
        if b_clips:
            final_video = mp.concatenate_videoclips(b_clips, method="compose")
            final_video = final_video.set_audio(audio_a)
            
            if text_content:
                txt_clip = mp.TextClip(text_content, fontsize=24, color='white', font='Montserrat')
                txt_clip = txt_clip.set_pos('center').set_duration(final_video.duration)
                final_video = mp.CompositeVideoClip([final_video, txt_clip])
                
            return final_video
        return None
    except Exception as e:
        st.error(f"Có lỗi xảy ra trong quá trình render: {str(e)}")
        return None

# --- 3. NÚT BẤM RENDER VIDEO ---
st.markdown("---")
if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True):
    if not video_a_file or not video_b_files:
        st.warning("Vui lòng tải đầy đủ cả Video A và ít nhất 1 Video B để tiến hành trộn ghép!")
    else:
        with st.spinner("Hệ thống đang xử lý, cắt ghép và trộn video... Vui lòng đợi trong giây lát!"):
            # Tạo file tạm để xử lý dữ liệu đầu vào
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_a:
                tmp_a.write(video_a_file.read())
                video_a_path = tmp_a.name
                
            video_b_paths = []
            for f in video_b_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_b:
                    tmp_b.write(f.read())
                    video_b_paths.append(tmp_b.name)
            
            # Chạy hàm render
            output_video = process_video(video_a_path, video_b_paths, text_content, text_style)
            
            if output_video:
                output_path = "output_koc_final.mp4"
                output_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
                
                st.success("🎉 Video KOC đã được tạo thành công!")
                # Hiện nút tải video về máy
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 TẢI VIDEO HOÀN THIỆN VỀ MÁY",
                        data=file,
                        file_name="koc_marketing_video.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )