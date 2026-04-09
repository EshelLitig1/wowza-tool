import streamlit as st
import random
import re

st.set_page_config(page_title="Wowza Interlaced Converter", layout="wide")

# --- 🔄 RESET LOGIC ---
if st.sidebar.button("Sweep 🧹 Clear All Fields"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- 🎰 THE LOGO GAME ---
st.sidebar.markdown("### 🎲 Mini Game")
correct_order = ["logo_top.jpg", "logo_middle.jpg", "logo_bottom.jpg"]
if "current_order" not in st.session_state:
    st.session_state.current_order = correct_order.copy()

if st.sidebar.button("🎰 Spin the Logos!"):
    random.shuffle(st.session_state.current_order)
    if st.session_state.current_order == correct_order:
        st.balloons() 
        st.sidebar.success("🎉 JACKPOT!")

s_col1, s_col2, s_col3 = st.sidebar.columns(3)
with s_col1: st.image(st.session_state.current_order[0], use_container_width=True)
with s_col2: st.image(st.session_state.current_order[1], use_container_width=True)
with s_col3: st.image(st.session_state.current_order[2], use_container_width=True)

st.sidebar.divider()

# --- MAIN APP ---
st.title("🎥 FFmpeg Command Generator")

col1, col2, col3 = st.columns(3)

# --- 1. INPUT SOURCE ---
with col1:
    st.header("1. Input Source")
    input_host = st.text_input("Input Host/IP", value="54.156.246.82")
    input_port = st.text_input("Input Port", value="37301")
    
    add_passphrase = st.checkbox("Add passphrase?", value=True)
    passphrase = st.text_input("Passphrase", value="ch301_wsc_y84fmq1") if add_passphrase else ""

# --- 2. ENCODING SETTINGS ---
with col2:
    st.header("2. Encoding")
    # ADDED: Tooltip for "Convert video?"
    should_convert = st.checkbox(
        "Convert video? (Not copy)", 
        value=True,
        help="Uncheck if the video doesn't need to be converted"
    )
    
    if should_convert:
        is_interlaced = st.checkbox("Is interlaced?", value=True)
        bwdif_mode = 1
        if is_interlaced:
            bwdif_mode = st.selectbox(
                "BWDIF/YADIF Mode", 
                options=[0, 1], 
                index=1,
                help="Mode 0: Standard frame rate. Mode 1: Double frame rate (smoother motion, turns 30i into 60p)."
            )
            
        st.caption("Video Parameters")
        fps_selection = st.selectbox(
            "FPS Value",
            options=["60", "60000/1001", "30", "30000/1001", "50", "25"],
            index=3
        )
    
    # Audio Logic (Independent of should_convert)
    st.divider()
    st.caption("Audio Parameters")
    is_multi_audio = st.checkbox("Is multi audio", value=False)
    num_audio_tracks = 1
    if is_multi_audio:
        num_audio_tracks = st.number_input("Num of stereo tracks", min_value=1, value=2, step=1)
        
    audio_codec = st.text_input("Audio Codec", value="aac")
    audio_bitrate = st.text_input("Audio Bitrate", value="192k")

# --- 3. OUTPUT PATH ---
with col3:
    st.header("3. Output Path")
    app_name = st.text_input("Application name", value="live")
    stream_name = st.text_input("Stream file name", value="stream")
    
    pattern = re.compile(r"^[a-zA-Z]+$")
    valid_input = True
    if app_name and not pattern.match(app_name):
        st.error("Application name must be letters only.")
        valid_input = False
    if stream_name and not pattern.match(stream_name):
        st.error("Stream file name must be letters only.")
        valid_input = False

# --- GENERATE COMMAND LOGIC ---
st.divider()

if valid_input:
    srt_input = f"srt://{input_host}:{input_port}"
    if add_passphrase and passphrase:
        srt_input += f"?passphrase={passphrase}"

    video_flags = ""
    if should_convert:
        if is_interlaced:
            video_flags += f" -vf bwdif=mode={bwdif_mode}"
        
        gop_map = {"60": "60", "60000/1001": "60", "30": "30", "30000/1001": "30", "50": "50", "25": "25"}
        gop_val = gop_map.get(fps_selection, "30")
        video_flags += f" -vcodec h264_nvenc -s 1920x1080 -rc:v vbr -cq:v 20 -maxrate 15000000 -pix_fmt yuv420p -r {fps_selection} -g {gop_val}"
    else:
        video_flags += " -vcodec copy"

    video_flags += f" -acodec {audio_codec} -b:a {audio_bitrate}"
    
    if not is_multi_audio:
        video_flags += " -map v:0 -map a:0"
    else:
        mapping_str = " -map v:0"
        for i in range(int(num_audio_tracks)):
            mapping_str += f" -map a:{i}"
        video_flags += mapping_str

    ffmpeg_value = video_flags.strip()
    hls_preview_url = f"https://windows.net{app_name}/{stream_name}/stream.m3u8"

    out_col1, out_col2 = st.columns(2)
    with out_col1:
        st.subheader("📄 YAML Configuration")
        final_yaml = f"name: {stream_name}\ninput: {srt_input}\nffmpegcommand: {ffmpeg_value}\noutputhls_path: hls/{app_name}/{stream_name}"
        st.code(final_yaml, language="yaml")
    with out_col2:
        st.subheader("🔗 HLS Playlist Preview")
        st.code(hls_preview_url, language="text")
else:
    st.warning("⚠️ Please fix the naming errors in Section 3.")
