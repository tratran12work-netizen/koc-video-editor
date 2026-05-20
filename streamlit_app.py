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
st.markdown("Công cụ trộn ghép video - Tự động lưu trạng thái, không lo mất dữ liệu khi F5/Reload trang!")

# --- ĐỊNH NGHĨA KÍCH THƯỚC KHUNG HÌNH CHUẨN ĐẦU RA ---
TARGET_W, TARGET_H = 1080, 1920

# --- KHỞI TẠO KHÔNG GIAN LƯU TRỮ TRẠNG THÁI (SESSION STATE) ---
if "video_a_path" not in st.session_state:
    st.session_state.video_a_path = None
if "video_a_name" not in st.session_state:
    st.session_state.video_a_name = None
if "max_duration" not in st.session_state:
    st.session_state.max_duration = 60.0
if "trim_start" not in st.session_state:
    st.session_state.trim_start = 0.0
if "trim_end" not in st.session_state:
    st.session_state.trim_end = 15.0

if "uploaded_b_files" not in st.session_state:
    # Lưu danh sách thông tin video B dưới dạng bytes để không bị giải phóng khi F5
    st.session_state.uploaded_b_files = []
if "b_configs" not in st.session_state:
    st.session_state.b_configs = {}

if "text_content" not in st.session_state:
    st.session_state.text_content = ""
if "text_style" not in st.session_state:
    st.session_state.text_style = "Chữ Trắng - Viền Xanh"

# --- 1. TẢI VIDEO SOURCE (VIDEO A) ---
st.header("1. Bước 1: Thiết lập Video Voice (Video A)")

# Hiện trạng thái file đã tải trước đó nếu có
if st.session_state.video_a_name:
    st.info(f"📁 Video A hiện tại đang lưu: `{st.session_state.video_a_name}`")

video_a_file = st.file_uploader("Tải Video A mới (Lấy Audio/Voice gốc)", type=["mp4", "mov", "mpeg4"])

if video_a_file:
    # Nếu có file mới tải lên, tiến hành lưu đè vào session_state
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_a:
        tmp_a.write(video_a_file.getvalue())
        st.session_state.video_a_path = tmp_a.name
        st.session_state.video_a_name = video_a_file.name
    try:
        clip_info = mp.VideoFileClip(st.session_state.video_a_path)
        st.session_state.max_duration = float(clip_info.duration)
        st.session_state.trim_end = min(15.0, st.session_state.max_duration)
        clip_info.close()
    except:
        st.session_state.max_duration = 60.0
    st.rerun()

# Hiển thị trình cấu hình Video A dựa trên Session State
if st.session_state.video_a_path and os.path.exists(st.session_state.video_a_path):
    st.markdown("### 📺 Xem video để nghe và lấy mốc thời gian của Voice:")
    st.video(st.session_state.video_a_path)
    st.markdown(f"**Tổng thời lượng gốc:** `{st.session_state.max_duration:.1f}` giây")
    
    st.session_state.trim_start, st.session_state.trim_end = st.slider(
        "Kéo để chọn đoạn Voice muốn giữ lại (giây):", 
        min_value=0.0, 
        max_value=st.session_state.max_duration, 
        value=(st.session_state.trim_start, min(st.session_state.trim_end, st.session_state.max_duration)), 
        step=0.1
    )
    voice_duration = st.session_state.trim_end - st.session_state.trim_start
    st.info(f"⏱️ Tổng độ dài đoạn Voice đã chọn: **{voice_duration:.1f} giây**")

st.markdown("---")

# --- 2. TẢI VIDEO B VÀ TỰ ĐỘNG PHÂN TÍCH BLOCK 5S ---
st.header("2. Bước 2: Tải Video B và Phân tích Block 5 giây")
video_b_files = st.file_uploader("Tải các Video B (Lấy hình ảnh minh họa)", type=["mp4", "mov", "mpeg4"], accept_multiple_files=True)

if video_b_files:
    # Chuyển đổi dữ liệu sang dạng bộ nhớ tạm cố định để không bị bay màu khi F5
    new_b_list = []
    for f in video_b_files:
        file_bytes = f.getvalue()
        new_b_list.append({"name": f.name, "bytes": file_bytes})
    st.session_state.uploaded_b_files = new_b_list
    st.rerun()

# Biến tạm để tổng hợp danh sách render ngầm
b_segments_to_render = {}
segment_counter = 0

if st.session_state.uploaded_b_files:
    st.markdown("### 🧠 Kết quả tự động băm nhỏ Clip B mỗi 5 giây:")
    
    for i, f_data in enumerate(st.session_state.uploaded_b_files):
        f_name = f_data["name"]
        f_bytes = f_data["bytes"]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_analysis:
            tmp_analysis.write(f_bytes)
            analysis_path = tmp_analysis.name
            
        try:
            clip_b_info = mp.VideoFileClip(analysis_path)
            duration_b = float(clip_b_info.duration)
            clip_b_info.close()
        except:
            duration_b = 15.0
            
        st.markdown(f"#### 📂 File gốc: `{f_name}` (Dài {duration_b:.1f}s)")
        
        start_time = 0.0
        block_idx = 1
        
        while start_time < duration_b:
            end_time = min(start_time + 5.0, duration_b)
            if (end_time - start_time) >= 1.0:
                block_key = f"{f_name}_block_{block_idx}"
                
                # Khởi tạo cấu hình mặc định an toàn cho block nếu chưa từng tồn tại
                if block_key not in st.session_state.b_configs:
                    if block_idx == 1:
                        def_label = "Cảnh mở đầu - Cận cảnh KOC và sản phẩm"
                    elif block_idx == 2:
                        def_label = "Cảnh chi tiết - Cận cảnh lòng máy/động cơ quay"
                    else:
                        def_label = "Cảnh trải nghiệm - Thao tác đổ hạt/uống sữa thành phẩm"
                        
                    st.session_state.b_configs[block_key] = {
                        "label": def_label,
                        "target_start": min(0.0 + (segment_counter * 3.0), st.session_state.max_duration)
                    }
                
                with st.container():
                    col_info, col_sync = st.columns([1.3, 1.0])
                    
                    with col_info:
                        st.info(f"🎞️ Phân khúc {block_idx} (Đoạn {start_time:.1f}s - {end_time:.1f}s)")
                        # Đồng bộ trực tiếp text_input với session_state
                        st.session_state.b_configs[block_key]["label"] = st.text_input(
                            f"Tên phân cảnh nhận diện:", 
                            value=st.session_state.b_configs[block_key]["label"], 
                            key=f"input_label_{block_key}"
                        )
                        
                    with col_sync:
                        st.markdown("**🎯 Khớp đè lên Video A:**")
                        # Thêm khóa chặn chặn đứng hoàn toàn lỗi StreamlitAPIException vượt quá max_value khi F5
                        st.session_state.b_configs[block_key]["target_start"] = st.number_input(
                            f"Xuất hiện tại giây thứ (trên Video A):", 
                            min_value=0.0, 
                            max_value=st.session_state.max_duration, 
                            value=min(st.session_state.b_configs[block_key]["target_start"], st.session_state.max_duration), 
                            key=f"input_start_{block_key}"
                        )
                        target_end = st.session_state.b_configs[block_key]["target_start"] + (end_time - start_time)
                        st.caption(f"Sẽ kết thúc tại: {target_end:.1f}s")
                        
                    # Gán vào từ điển để chuẩn bị ném vào hàm xử lý render phim
                    b_segments_to_render[block_key] = {
                        "file_bytes": f_bytes,
                        "b_start": start_time,
                        "b_end": end_time,
                        "target_start": st.session_state.b_configs[block_key]["target_start"],
                        "target_end": target_end
                    }
                    
                st.markdown("---")
                segment_counter += 1
                block_idx += 1
            start_time += 5.0

st.markdown("---")

# --- 3. CÀI ĐẶT TEXT CHÈN LÊN VIDEO ---
st.header("3. Bước 3: Cài đặt phụ đề / Text")
st.session_state.text_content = st.text_area(
    "Nhập nội dung Text chèn lên giữa video", 
    value=st.session_state.text_content,
    placeholder="Ví dụ: CẬN CẢNH LÒNG MÁY XỊN SÒ...",
    key="main_text_content"
)
st.session_state.text_style = st.selectbox(
    "Chọn Style Text", 
    ["Chữ Trắng - Viền Xanh", "Chữ Vàng - Viền Đen"],
    index=0 if st.session_state.text_style == "Chữ Trắng - Viền Xanh" else 1,
    key="main_text_style"
)

# --- HÀM ÉP VIDEO VỪA KHÍT CĂNG ĐÉT KHUNG 9:16 (CROP PHÓNG TO KHÔNG MÉO HÌNH) ---
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

# --- HÀM XỬ LÝ VIDEO NGẦM ---
def process_video(video_a_path, b_segments, text_content, text_style):
    try:
        clip_a = mp.VideoFileClip(video_a_path)
        trim_start = st.session_state.trim_start
        trim_end = st.session_state.trim_end
        clip_a_cut = clip_a.subclip(trim_start, min(trim_end, clip_a.duration))
            
        audio_a = clip_a_cut.audio
        total_final_duration = clip_a_cut.duration
        
        composite_layers = []
        
        for name, config in b_segments.items():
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_b:
                tmp_b.write(config["file_bytes"])
                b_path = tmp_b.name
            
            clip_b_raw = mp.VideoFileClip(b_path)
            sub_b = clip_b_raw.subclip(config["b_start"], min(config["b_end"], clip_b_raw.duration))
            
            # Phóng to phủ kín màn hình dọc 9:16
            sub_b_filled = crop_to_fill_9_16(sub_b)
            
            # Cân chỉnh mốc thời gian xuất hiện đè lên trục voice gốc
            sub_b_positioned = sub_b_filled.set_start(config["target_start"] - trim_start).set_duration(sub_b.duration)
            composite_layers.append(sub_b_positioned)
        
        if text_content:
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
    if not st.session_state.video_a_path or not b_segments_to_render:
        st.warning("Vui lòng tải đầy đủ dữ liệu Video đầu vào!")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("⚙️ Bước 1/4: Đang trích xuất dữ liệu Voice từ Video A...")
            progress_bar.progress(15)
            
            status_text.text("⚙️ Bước 2/4: Đang băm cảnh 5s và ép lấp đầy 100% khung hình dọc 9:16 cho Video B...")
            progress_bar.progress(40)
            
            final_video, duration = process_video(st.session_state.video_a_path, b_segments_to_render, st.session_state.text_content, st.session_state.text_style)
            
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