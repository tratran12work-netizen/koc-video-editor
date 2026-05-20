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
st.markdown("Bản tối ưu tuyệt đối: Lấy 100% Voice Video A + Tự động khớp cảnh Video B + Không chèn Text")

# --- ĐỊNH NGHĨA KÍCH THƯỚC KHUNG HÌNH CHUẨN ĐẦU RA ---
TARGET_W, TARGET_H = 1080, 1920

# --- KHỞI TẠO KHÔNG GIAN LƯU TRỮ TRẠNG THÁI (SESSION STATE) ---
if "video_a_path" not in st.session_state:
    st.session_state.video_a_path = None
if "video_a_name" not in st.session_state:
    st.session_state.video_a_name = None
if "uploaded_b_files" not in st.session_state:
    st.session_state.uploaded_b_files = []

# --- 1. TẢI VIDEO SOURCE (VIDEO A) ---
st.header("1. Bước 1: Tải Video Voice (Video A)")

if st.session_state.video_a_name:
    st.info(f"📁 Video A đang lưu: `{st.session_state.video_a_name}`")

video_a_file = st.file_uploader("Tải Video A (Lấy 100% Audio/Voice gốc)", type=["mp4", "mov", "mpeg4"])

if video_a_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_a:
        tmp_a.write(video_a_file.getvalue())
        st.session_state.video_a_path = tmp_a.name
        st.session_state.video_a_name = video_a_file.name
    st.rerun()

# Hiển thị trình phát Video A trực quan
if st.session_state.video_a_path and os.path.exists(st.session_state.video_a_path):
    st.markdown("### 📺 Trình xem trước Video A:")
    st.video(st.session_state.video_a_path)

st.markdown("---")

# --- 2. TẢI VIDEO B (LƯU TRỮ TĨNH SIÊU NHẸ) ---
st.header("2. Bước 2: Tải các Video B để đắp cảnh")
video_b_files = st.file_uploader("Tải các Video B (Hệ thống tự động chia đều thời gian và fit khung hình)", type=["mp4", "mov", "mpeg4"], accept_multiple_files=True)

if video_b_files:
    new_b_list = []
    for f in video_b_files:
        new_b_list.append({"name": f.name, "bytes": f.getvalue()})
    st.session_state.uploaded_b_files = new_b_list
    st.rerun()

if st.session_state.uploaded_b_files:
    st.success(f"📂 Đã nhận {len(st.session_state.uploaded_b_files)} Video B. Sẵn sàng tự động phân phối khít theo trục Voice A.")
    for item in st.session_state.uploaded_b_files:
        st.caption(f"✓ {item['name']}")

# --- HÀM ÉP VIDEO VỪA KHÍT CĂNG ĐÉT KHUNG 9:16 (CROP KHÔNG MÉO) ---
def crop_to_fill_9_16(clip):
    video_w, video_h = clip.size
    target_ratio = TARGET_W / TARGET_H
    video_ratio = video_w / video_h
    
    if video_ratio > target_ratio:
        new_h = TARGET_H
        new_w = int(TARGET_H * video_ratio)
        clip_resized = clip.resize(height=new_h)
        return clip_resized.crop(x_center=new_w / 2, y_center=TARGET_H / 2, width=TARGET_W, height=TARGET_H)
    else:
        new_w = TARGET_W
        new_h = int(TARGET_W / video_ratio)
        clip_resized = clip.resize(width=new_w)
        return clip_resized.crop(x_center=TARGET_W / 2, y_center=new_h / 2, width=TARGET_W, height=TARGET_H)

# --- HÀM TỰ ĐỘNG PHÂN PHỐI LỚP VIDEO THEO TIMELINE GỐC ---
def auto_process_video(video_a_path, uploaded_b_list):
    try:
        # Lấy toàn bộ 100% thời lượng của Video A
        clip_a = mp.VideoFileClip(video_a_path)
        audio_a = clip_a.audio
        total_duration = clip_a.duration
        
        # Tự động chia đều thời gian xuất hiện dựa trên số lượng Video B up lên
        num_b = len(uploaded_b_list)
        duration_per_b = total_duration / num_b
        
        composite_layers = []
        current_timeline = 0.0
        
        for b_data in uploaded_b_list:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_b:
                tmp_b.write(b_data["bytes"])
                b_path = tmp_b.name
            
            clip_b_raw = mp.VideoFileClip(b_path)
            # Lấy đoạn khớp từ đầu của mỗi Video B tương ứng với thời gian được chia đều
            sub_b = clip_b_raw.subclip(0, min(duration_per_b, clip_b_raw.duration))
            
            # Phóng to phủ kín hoàn toàn màn hình dọc 9:16 không méo hình
            sub_b_filled = crop_to_fill_9_16(sub_b)
            # Tự động xếp nối đuôi nhau chuẩn xác trên dòng thời gian tổng
            sub_b_positioned = sub_b_filled.set_start(current_timeline).set_duration(duration_per_b)
            composite_layers.append(sub_b_positioned)
            
            current_timeline += duration_per_b
            
        final_video = mp.CompositeVideoClip(composite_layers, size=(TARGET_W, TARGET_H))
        final_video = final_video.set_audio(audio_a)
        return final_video
        
    except Exception as e:
        st.error(f"Lỗi tự động cấu hình Layer: {str(e)}")
        return None

# --- 3. NÚT BẤM VÀ XỬ LÝ TIẾN TRÌNH RENDER ---
st.markdown("---")
if st.button("🚀 BẮT ĐẦU TẠO VIDEO TỰ ĐỘNG", use_container_width=True):
    if not st.session_state.video_a_path or not st.session_state.uploaded_b_files:
        st.warning("Vui lòng cung cấp đầy đủ Video A và Video B đầu vào!")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("⚙️ Bước 1/3: Hệ thống đang tự động tính toán thời lượng khít 100% voice...")
            progress_bar.progress(30)
            
            final_video = auto_process_video(st.session_state.video_a_path, st.session_state.uploaded_b_files)
            
            if final_video:
                status_text.text("⚙️ Bước 2/3: Đang tiến hành nén xuất clip tràn khung 9:16...")
                progress_bar.progress(65)
                
                output_path = "output_koc_auto_final.mp4"
                final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                progress_bar.progress(100)
                status_text.text("🎉 Đã xuất video tự động hoàn thiện thành công!")
                
                st.markdown("---")
                st.header("📺 Xem trước kết quả Video hoàn thành")
                st.video(output_path)
                
                st.balloons()
                
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 BẤM VÀO ĐÂY ĐỂ TẢI VIDEO HOÀN THÀNH VỀ MÁY",
                        data=file,
                        file_name="koc_auto_perfect_916.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Có lỗi hệ thống xảy ra trong quá trình render phim: {str(e)}")