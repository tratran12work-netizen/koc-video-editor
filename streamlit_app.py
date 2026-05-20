import streamlit as st
import moviepy.editor as mp
import tempfile
import os

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="KOC Video Editor", layout="centered")
st.title("🎬 KOC Video Generator Pro")
st.markdown("Công cụ cắt ghép video tự động dành cho Marketing")

# --- HÀM XỬ LÝ VIDEO ---
def process_video(video_a_path, video_b_paths, text_content, text_style, trim_start, trim_end):
    try:
        # 1. Xử lý Video A (Lấy Audio)
        clip_a = mp.VideoFileClip(video_a_path)
        if trim_start > 0 or trim_end < clip_a.duration:
            clip_a = clip_a.subclip(trim_start, trim_end)
        audio_a = clip_a.audio

        # 2. Xử lý Video B (Cắt 10-15s mỗi clip)
        b_clips = []
        for path in video_b_paths:
            clip = mp.VideoFileClip(path)
            # Lấy 15s đầu hoặc toàn bộ nếu clip ngắn hơn 15s
            duration = min(15, clip.duration) 
            cut_clip = clip.subclip(0, duration)
            # Resize về chung một chuẩn để tránh lỗi khi ghép (ví dụ 720x1280 - tỷ lệ TikTok)
            cut_clip = cut_clip.resize(height=1280, width=720) 
            b_clips.append(cut_clip)

        # 3. Ghép các Video B lại
        final_visual = mp.concatenate_videoclips(b_clips, method="compose")
        
        # Cắt hình ảnh của Video B sao cho khớp với độ dài Audio A
        if final_visual.duration > clip_a.duration:
            final_visual = final_visual.subclip(0, clip_a.duration)
            
        # Gắn Audio A vào Hình ảnh B
        final_video = final_visual.set_audio(audio_a)

        # 4. Xử lý Text
        # Lưu ý: Cần có font Montserrat cài đặt trên hệ thống hoặc upload file .ttf
        font_name = "Montserrat" 
        
        text_clip_params = {
            "txt": text_content,
            "font": font_name,
            "fontsize": 60,
            "size": (600, None),
            "method": "caption"
        }

        if text_style == "Chữ Trắng - Viền Xanh":
            text_clip = mp.TextClip(**text_clip_params, color='white', stroke_color='blue', stroke_width=2)
        elif text_style == "Chữ Đỏ - Viền Trắng":
            text_clip = mp.TextClip(**text_clip_params, color='red', stroke_color='white', stroke_width=2)
        elif text_style == "Chữ Trắng - Nền Xanh Lá":
            text_clip = mp.TextClip(**text_clip_params, color='white', bg_color='green')
        elif text_style == "Chữ Trắng - Nền Đỏ":
            text_clip = mp.TextClip(**text_clip_params, color='white', bg_color='red')
        else: # Option 5: Chữ Vàng - Nền Đen
            text_clip = mp.TextClip(**text_clip_params, color='yellow', bg_color='black')

        text_clip = text_clip.set_position(('center', 'bottom')).set_duration(final_video.duration)
        
        # 5. Xuất Video
        final_output = mp.CompositeVideoClip([final_video, text_clip])
        
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        # Dùng preset ultrafast để tối ưu tốc độ trên Streamlit free
        final_output.write_videofile(output_path, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
        
        # Dọn dẹp RAM
        clip_a.close()
        for c in b_clips:
            c.close()
            
        return output_path
    except Exception as e:
        return str(e)

# --- GIAO DIỆN NGƯỜI DÙNG ---

# 1. TẢI VIDEO LÊN
st.subheader("1. Tải Video Source")
col1, col2 = st.columns(2)

with col1:
    video_a_file = st.file_uploader("Video A (Lấy Audio)", type=["mp4", "mov"])
with col2:
    video_b_files = st.file_uploader("Video B (Tối đa 10 clip lấy hình)", type=["mp4", "mov"], accept_multiple_files=True)
    if len(video_b_files) > 10:
        st.error("Chỉ được tải lên tối đa 10 clip B!")

# KHU VỰC CẮT VIDEO A (Yêu cầu 6)
trim_start, trim_end = 0.0, 0.0
if video_a_file is not None:
    # Lưu tạm ra disk để lấy thông tin duration
    tfile_a = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile_a.write(video_a_file.read())
    clip_info = mp.VideoFileClip(tfile_a.name)
    duration_a = clip_info.duration
    clip_info.close()
    
    st.info(f"Thời lượng Video A: {duration_a:.1f} giây")
    
    if duration_a > 60:
        st.warning("⚠️ Video A dài hơn 60s. Khuyến nghị nên cắt bớt để ứng dụng không bị quá tải.")
        
    st.write("Cắt Video A (Tùy chọn):")
    trim_start, trim_end = st.slider("Chọn đoạn muốn giữ lại (giây)", 0.0, float(duration_a), (0.0, float(duration_a)))

# 2. OPTION TEXT (Yêu cầu 2)
st.subheader("2. Cài đặt Text")
text_content = st.text_area("Nhập nội dung Text chèn lên video", "Mẫu nội dung KOC...")
text_options = [
    "Chữ Trắng - Viền Xanh", 
    "Chữ Đỏ - Viền Trắng", 
    "Chữ Trắng - Nền Xanh Lá", 
    "Chữ Trắng - Nền Đỏ",
    "Chữ Vàng - Nền Đen"
]
selected_style = st.selectbox("Chọn Style Text (Font Montserrat)", text_options)

st.divider()

# 3, 4, 5. NÚT BẮT ĐẦU & TIẾN ĐỘ & PREVIEW
if st.button("🚀 BẮT ĐẦU TẠO VIDEO", use_container_width=True, type="primary"):
    if not video_a_file or not video_b_files:
        st.error("Vui lòng upload đầy đủ Video A và ít nhất 1 Video B.")
    elif len(video_b_files) > 10:
        st.error("Vui lòng xóa bớt Video B, tối đa chỉ 10 clip.")
    else:
        # Hiển thị spinner (vòng tròn tiến độ đang quay)
        with st.spinner("Đang xử lý âm thanh, cắt hình ảnh và render... Vui lòng không đóng trang này!"):
            
            # Lưu các file B ra ổ tạm
            b_paths = []
            for b_file in video_b_files:
                tfile_b = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile_b.write(b_file.read())
                b_paths.append(tfile_b.name)
            
            # Thực thi ghép video
            result_path = process_video(tfile_a.name, b_paths, text_content, selected_style, trim_start, trim_end)
            
            if result_path.endswith(".mp4"):
                st.success("✅ Đã hoàn thành!")
                
                # Hiển thị Video
                st.subheader("Kết quả Video")
                st.video(result_path)
                
                # Nút Download
                with open(result_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Tải Video về máy",
                        data=file,
                        file_name="KOC_Generated_Video.mp4",
                        mime="video/mp4",
                        type="primary"
                    )
            else:
                st.error(f"Có lỗi xảy ra trong quá trình render: {result_path}")
