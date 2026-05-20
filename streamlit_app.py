import PIL.Image
# Vá lỗi tương thích phiên bản Pillow mới để không bị sập khi render video
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import tempfile
import os
import streamlit as st
from moviepy import editor as mp

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="KOC Video Editor Pro", layout="centered")
st.title("🎬 KOC Video Generator Pro v2")
st.markdown("Công cụ trộn ghép, đồng bộ cảnh theo Voice và giữ nguyên 100% size video gốc trên khung dọc 9:16")

# --- 1. TẢI VIDEO SOURCE ---
st.header("1. Bước 1: Thiết lập Video Voice (Video A)")
video_a_file = st.file_uploader("Tải Video A (Lấy Audio/Voice gốc)", type=["mp4", "mov", "mpeg4"])

if video_a_file:
    st.success("🎉 Tải thành công Video A!")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_preview_a:
        tmp_preview_a.write(video_a_file.getvalue())
        video_a_preview_path = tmp_preview_a.name
    
    try:
        clip_info = mp.VideoFileClip(video_a_preview_path)
        max_duration = float(clip_info.duration)
        clip_info.close()
    except:
        max_duration = 60.0
    
    st.markdown("### 📺 Xem video để nghe và lấy mốc thời gian của Voice:")
    st.video(video_a_preview_path)
    st.markdown(f"**Tổng thời lượng gốc:** `{max_duration:.1f}` giây")
    
    st.session_state.trim_start, st.session_state.trim_end = st.slider(
        "Kéo để chọn đoạn Voice muốn giữ lại (giây):", 
        min_value=0.0, max_value=max_duration, value=(0.0, min(15.0, max_duration)), step=0.1
    )
    voice_duration = st.session_state.trim_end - st.session_state.trim_start
    st.info(f"⏱️ Tổng độ dài đoạn Voice đã chọn: **{voice_duration:.1f} giây**")

st.markdown("---")

# --- 2. TẢI VIDEO B VÀ KHỚP CẢNH THEO VOICE ---
st.header("2. Bước 2: Tải Video B cảnh nền và Khớp dòng thời gian")
video_b_files = st.file_uploader("Tải các Video B (Lấy hình ảnh minh họa)", type=["mp4", "mov", "mpeg4"], accept_multiple_files=True)

# Tạo từ điển lưu mốc thời gian khớp cảnh của từng video B
b_segments = {}

if video_b_files:
    st.markdown("### 🎯 Sắp xếp cảnh Video B khớp với lời nói (Voice):")
    st.caption("Hãy điền mốc thời gian (giây) bạn muốn clip này xuất hiện đè lên Voice của Video A.")
    
    for i, f in enumerate(video_b_files):
        with st.container():
            st.markdown(f"**🎬 Clip B số {i+1}:** `{f.name}`")
            col1, col2 = st.columns(2)
            with col1:
                start_b = st.number_input(f"Xuất hiện từ giây thứ (trên Video A)", min_value=0.0, max_value=max_duration, value=0.0 + (i*3.0), key=f"start_{i}")
            with col2:
                end_b = st.number_input(f"Biến mất ở giây thứ (trên Video A)", min_value=0.0, max_value=max_duration, value=min(3.0 + (i*3.0), max_duration), key=f"end_{i}")
            b_segments[f.name] = {"start": start_b, "end": end_b, "file": f}
            st.markdown("---")

# --- 3. CÀI ĐẶT TEXT CHÈN LÊN VIDEO ---
st.header("3. Bước 3: Cài đặt phụ đề / Text")
text_content = st.text_area("Nhập nội dung Text chèn lên giữa video", placeholder="Ví dụ: CẬN CẢNH LÒNG MÁY XỊN SÒ...")
text_style = st.selectbox("Chọn Style Text", ["Chữ Trắng - Viền Xanh", "Chữ Vàng - Viền Đen"])

# --- HÀM XỬ LÝ KHUNG HÌNH NỀN 9:16 GIỮ NGUYÊN SIZE VIDEO GỐC 100% ---
def setup_frame_9_16(clip):
    target_w, target_h = 1080, 1920
    # Giữ nguyên 100% kích thước gốc của video, đặt chính giữa khung hình nền dọc 9:16 trống
    return clip.on_color(size=(target_w, target_h), color=(0,0,0), pos="center")

# --- HÀM XỬ LÝ VIDEO NGẦM ---
def process_video(video_a_path, b_segments, text_content, text_style):
    try:
        # Xử lý Video A (Lấy Audio/Voice)
        clip_a = mp.VideoFileClip(video_a_path)
        if 'trim_start' in st.session_state and 'trim_end' in st.session_state:
            trim_start = st.session_state.trim_start
            trim_end = st.session_state.trim_end
            clip_a_cut = clip_a.subclip(trim_start, min(trim_end, clip_a.duration))
        else:
            clip_a_cut = clip_a
            
        audio_a = clip_a_cut.audio
        total_final_duration = clip_a_cut.duration
        
        # Tạo khung hình nền dọc 9:16 trống chuẩn
        base_black_screen = mp.ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=total_final_duration)
        composite_layers = [base_black_screen]
        
        # Xử lý các Video B lấy hình ảnh giữ nguyên size gốc
        for name, config in b_segments.items():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_b:
                tmp_b.write(config["file"].getvalue())
                b_path = tmp_b.name
            
            duration_needed = config["end"] - config["start"]
            clip_b_raw = mp.VideoFileClip(b_path)
            sub_b = clip_b_raw.subclip(0, min(duration_needed, clip_b_raw.duration))
            
            # Gọi hàm đặt video gốc 100% vào giữa khung dọc
            sub_b_framed = setup_frame_9_16(sub_b)
            sub_b_positioned = sub_b_framed.set_start(config["start"] - st.session_state.trim_start).set_duration(duration_needed)
            composite_layers.append(sub_b_positioned)
        
        # Chèn thêm Text nếu có
        if text_content:
            txt_clip = mp.TextClip(text_content, fontsize=45, color='white', font='Montserrat', bg_color='black')
            txt_clip = txt_clip.set_pos(('center', 1500)).set_start(0).set_duration(total_final_duration)
            composite_layers.append(txt_clip)
        
        final_video = mp.CompositeVideoClip(composite_layers, size=(1080, 1920))
        final_video = final_video.set_audio(audio_a)
        return final_video, total_final_duration
        
    except Exception as e:
        st.error(f"Có lỗi xảy ra trong quá trình cấu hình layer: {str(e)}")
        return None, 0

# --- 4. NÚT BẤM VÀ XỬ LÝ TIẾN TRÌNH RENDER ---
st.markdown("---")
if st.button("🚀 BẮT ĐẦU TẠO VIDEO HOÀN CHỈNH", use_container_width=True):
    if not video_a_file or not video_b_files:
        st.warning("Vui lòng tải đầy đủ dữ liệu Video đầu vào!")
    else:
        # Khởi tạo thanh phần trăm tiến độ hoàn thành trực quan
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("⚙️ Bước 1/4: Đang trích xuất dữ liệu Voice từ Video A...")
            progress_bar.progress(15)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_a:
                tmp_a.write(video_a_file.getvalue())
                video_a_path = tmp_a.name
            
            status_text.text("⚙️ Bước 2/4: Đang xử lý bóc tách và xếp đặt video B theo size gốc 100%...")
            progress_bar.progress(40)
            
            final_video, duration = process_video(video_a_path, b_segments, text_content, text_style)
            
            if final_video:
                status_text.text("⚙️ Bước 3/4: Đang tổng hợp các lớp hình ảnh và trộn âm thanh nền...")
                progress_bar.progress(70)
                
                status_text.text("⚙️ Bước 4/4: Đang mã hóa nén dữ liệu video (Render MP4)... Vui lòng đợi trong giây lát!")
                progress_bar.progress(85)
                
                output_path = "output_koc_super_final.mp4"
                final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                # Đạt 100% tiến độ thành công
                progress_bar.progress(100)
                status_text.text("🎉 Đã biên tập và xuất video hoàn thiện thành công!")
                
                # --- HIỂN THỊ KẾT QUẢ XEM TRƯỚC TRỰC TIẾP Ở DƯỚI ---
                st.markdown("---")
                st.header("📺 4. Bước 4: Xem trước kết quả Video hoàn thành")
                st.video(output_path)
                
                st.balloons()
                st.success("💡 Nếu bạn đã ưng ý với sản phẩm, hãy bấm nút dưới đây để tải về máy! Nếu chưa vừa ý, bạn chỉ cần chỉnh lại các số giây ở trên rồi bấm nút Tạo lại nhé.")
                
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 BẤM VÀO ĐÂY ĐỂ TẢI VIDEO HOÀN THÀNH VỀ MÁY",
                        data=file,
                        file_name="koc_final_916_perfect.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Có lỗi hệ thống xảy ra trong quá trình render: {str(e)}")