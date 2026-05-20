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
st.markdown("Công cụ trộn ghép, đồng bộ cảnh theo Voice và ép video vừa khít 100% khung dọc 9:16")

# --- ĐỊNH NGHĨA KÍCH THƯỚC KHUNG HÌNH CHUẨN ĐẦU RA ---
# Khung hình dọc chuẩn TikTok/Reels
TARGET_W, TARGET_H = 1080, 1920

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

# --- 2. TẢI VIDEO B VÀ TỰ ĐỘNG PHÂN TÍCH BLOCK 5S ---
st.header("2. Bước 2: Tải Video B và Phân tích Block 5 giây")
video_b_files = st.file_uploader("Tải các Video B (Lấy hình ảnh minh họa)", type=["mp4", "mov", "mpeg4"], accept_multiple_files=True)

# Từ điển lưu cấu hình dòng thời gian của từng block 5s
b_segments = {}
segment_counter = 0

if video_b_files:
    st.markdown("### 🧠 Kết quả tự động băm nhỏ Clip B mỗi 5 giây:")
    
    for i, f in enumerate(video_b_files):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_analysis:
            tmp_analysis.write(f.getvalue())
            analysis_path = tmp_analysis.name
            
        try:
            clip_b_info = mp.VideoFileClip(analysis_path)
            duration_b = float(clip_b_info.duration)
            clip_b_info.close()
        except:
            duration_b = 15.0
            
        st.markdown(f"#### 📂 File gốc: `{f.name}` (Dài {duration_b:.1f}s)")
        
        start_time = 0.0
        block_idx = 1
        
        while start_time < duration_b:
            end_time = min(start_time + 5.0, duration_b)
            if (end_time - start_time) >= 1.0:
                with st.container():
                    col_info, col_sync = st.columns([1.3, 1.0])
                    
                    with col_info:
                        st.info(f"🎞️ Phân khúc {block_idx} (Đoạn {start_time:.1f}s - {end_time:.1f}s)")
                        if block_idx == 1:
                            suggested_name = "Cảnh mở đầu - Cận cảnh KOC và sản phẩm"
                        elif block_idx == 2:
                            suggested_name = "Cảnh chi tiết - Cận cảnh lòng máy/động cơ quay"
                        else:
                            suggested_name = "Cảnh trải nghiệm - Thao tác đổ hạt/uống sữa thành phẩm"
                            
                        scene_label = st.text_input(f"Tên phân cảnh nhận diện:", value=suggested_name, key=f"label_{i}_{block_idx}")
                        
                    with col_sync:
                        st.markdown("**🎯 Khớp đè lên Video A:**")
                        target_start = st.number_input(f"Xuất hiện tại giây thứ (trên Video A):", min_value=0.0, max_value=max_duration, value=0.0 + (segment_counter * 3.0), key=f"target_start_{i}_{block_idx}")
                        target_end = target_start + (end_time - start_time)
                        st.caption(f"Sẽ kết thúc tại: {target_end:.1f}s")
                        
                    b_segments[f"{f.name}_block_{block_idx}"] = {
                        "file_bytes": f.getvalue(),
                        "b_start": start_time,
                        "b_end": end_time,
                        "target_start": target_start,
                        "target_end": target_end
                    }
                    
                st.markdown("---")
                segment_counter += 1
                block_idx += 1
            start_time += 5.0

st.markdown("---")

# --- 3. CÀI ĐẶT TEXT CHÈN LÊN VIDEO ---
st.header("3. Bước 3: Cài đặt phụ đề / Text")
text_content = st.text_area("Nhập nội dung Text chèn lên giữa video", placeholder="Ví dụ: CẬN CẢNH LÒNG MÁY XỊN SÒ...")
text_style = st.selectbox("Chọn Style Text", ["Chữ Trắng - Viền Xanh", "Chữ Vàng - Viền Đen"])

# --- HÀM ÉP VIDEO VỪA KHÍT CĂNG ĐÉT KHUNG 9:16 (CROP PHÓNG TO KHÔNG MÉO HÌNH) ---
def crop_to_fill_9_16(clip):
    # Tính toán tỉ lệ của video gốc
    video_w, video_h = clip.size
    target_ratio = TARGET_W / TARGET_H  # ~0.5625
    video_ratio = video_w / video_h
    
    if video_ratio > target_ratio:
        # Nếu video gốc là video ngang (16:9), phóng to chiều cao trước rồi crop chiều rộng
        new_h = TARGET_H
        new_w = int(TARGET_H * video_ratio)
        clip_resized = clip.resize(height=new_h)
        # Tiến hành cắt chính giữa để đưa về đúng 1080x1920
        return clip_resized.crop(x_center=new_w / 2, y_center=TARGET_H / 2, width=TARGET_W, height=TARGET_H)
    else:
        # Nếu video gốc đã là video dọc sẵn, phóng rộng chiều ngang rồi crop chiều cao
        new_w = TARGET_W
        new_h = int(TARGET_W / video_ratio)
        clip_resized = clip.resize(width=new_w)
        return clip_resized.crop(x_center=TARGET_W / 2, y_center=new_h / 2, width=TARGET_W, height=TARGET_H)

# --- HÀM XỬ LÝ VIDEO NGẦM ---
def process_video(video_a_path, b_segments, text_content, text_style):
    try:
        clip_a = mp.VideoFileClip(video_a_path)
        if 'trim_start' in st.session_state and 'trim_end' in st.session_state:
            trim_start = st.session_state.trim_start
            trim_end = st.session_state.trim_end
            clip_a_cut = clip_a.subclip(trim_start, min(trim_end, clip_a.duration))
        else:
            clip_a_cut = clip_a
            
        audio_a = clip_a_cut.audio
        total_final_duration = clip_a_cut.duration
        
        composite_layers = []
        
        for name, config in b_segments.items():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_b:
                tmp_b.write(config["file_bytes"])
                b_path = tmp_b.name
            
            clip_b_raw = mp.VideoFileClip(b_path)
            sub_b = clip_b_raw.subclip(config["b_start"], min(config["b_end"], clip_b_raw.duration))
            
            # Ép video B phóng to phủ kín hoàn toàn màn hình 9:16
            sub_b_filled = crop_to_fill_9_16(sub_b)
            
            # Thiết lập thời gian xuất hiện trên timeline tổng
            sub_b_positioned = sub_b_filled.set_start(config["target_start"] - st.session_state.trim_start).set_duration(sub_b.duration)
            composite_layers.append(sub_b_positioned)
        
        if text_content:
            # Chèn chữ phụ đề nổi lên trên cùng video, đặt ở vị trí dễ nhìn phía dưới màn hình
            txt_clip = mp.TextClip(text_content, fontsize=50, color='white', font='Montserrat', bg_color='black')
            txt_clip = txt_clip.set_pos(('center', 1600)).set_start(0).set_duration(total_final_duration)
            composite_layers.append(txt_clip)
        
        final_video = mp.CompositeVideoClip(composite_layers, size=(TARGET_W, TARGET_H))
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
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("⚙️ Bước 1/4: Đang trích xuất dữ liệu Voice từ Video A...")
            progress_bar.progress(15)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_a:
                tmp_a.write(video_a_file.getvalue())
                video_a_path = tmp_a.name
            
            status_text.text("⚙️ Bước 2/4: Đang băm cảnh 5s và ép lấp đầy 100% khung hình dọc 9:16 cho Video B...")
            progress_bar.progress(40)
            
            final_video, duration = process_video(video_a_path, b_segments, text_content, text_style)
            
            if final_video:
                status_text.text("⚙️ Bước 3/4: Đang tổng hợp các lớp hình ảnh và trộn âm thanh nền...")
                progress_bar.progress(70)
                
                status_text.text("⚙️ Bước 4/4: Đang mã hóa nén dữ liệu video (Render MP4)... Vui lòng đợi trong giây lát!")
                progress_bar.progress(85)
                
                output_path = "output_koc_super_final.mp4"
                final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
                
                progress_bar.progress(100)
                status_text.text("🎉 Đã biên tập và xuất video hoàn thiện thành công!")
                
                st.markdown("---")
                st.header("📺 4. Bước 4: Xem trước kết quả Video hoàn thành")
                st.video(output_path)
                
                st.balloons()
                st.success("💡 Nếu bạn đã ưng ý với sản phẩm, hãy bấm nút dưới đây để tải về máy!")
                
                with open(output_path, "rb") as file:
                    st.download_button(
                        label="📥 BẤM VÀO ĐÂY ĐỂ TẢI VIDEO HOÀN THÀNH VỀ MÁY",
                        data=file,
                        file_name="koc_final_full_916.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Có lỗi hệ thống xảy ra trong quá trình render: {str(e)}")