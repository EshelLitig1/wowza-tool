import streamlit as st
import random

st.set_page_config(page_title="Wowza Interlaced Converter", layout="wide")

# --- SIDEBAR: IMAGES & LINKS ---
with st.sidebar:
    # 🖼️ STATIC IMAGES (Brand Identity)
    st.image("logo_top.jpg", use_container_width=True)
    st.image("logo_middle.jpg", use_container_width=True)
    st.image("logo_bottom.jpg", use_container_width=True)
    
    st.divider()

    st.header("🔗 Reference Links")
    st.info("Quick access to configuration files & sheets:")
    
    st.markdown(
        """
        **wsc-ffmpeg-gpu-listener** [Open values.yaml ↗](https://wsc-zoomin.visualstudio.com/ZoomInCloud/_git/devops-argo?path=%2Fservices%2Fconfigurations%2Fwsc-mediaservices-prod-k8s-eus2%2Fwsc-ffmpeg-gpu-listeners%2Fvalues.yaml)
        """
    )
    
    st.markdown("---")
    
    st.markdown(
        """
        **wsc-wowza-gpu** [Open values.yaml ↗](https://wsc-zoomin.visualstudio.com/ZoomInCloud/_git/devops-argo?path=/services/configurations/wsc-mediaservices-prod-k8s-eus2/wsc-wowza-gpu/values.yaml)
        """
    )
    
    st.markdown("---")
    
    st.markdown(
        """
        **Wowza SRT Mapping (Sheet)** [Open Google Sheet ↗](https://docs.google.com/spreadsheets/d/1WP6HVIA5zrn87n2lDK-h2Mn9MpP9bON2-WeGx-yF2X8/edit?gid=0#gid=0)
        """
    )

# --- 🎰 THE LOGO GAME (Main Page Header) ---
st.markdown("### 🎲 Spin the Logos!")

# 1. Define the "Winning" order
correct_order = ["logo_top.jpg", "logo_middle.jpg", "logo_bottom.jpg"]

# 2. Initialize the state
if "current_order" not in st.session_state:
    st.session_state.current_order = correct_order.copy()

# 3. Game Controls
col_game_btn, col_game_msg = st.columns([1, 4])
with col_game_btn:
    if st.button("🎰 Spin!", help="Shuffle the images!"):
        random.shuffle(st.session_state.current_order)
        # Check for win immediately after shuffle
        if st.session_state.current_order == correct_order:
            st.balloons()
            st.toast("🎉 JACKPOT! Perfect Order!", icon="🏆")

# 4. Display Game Images (Small, Side-by-Side)
g_col1, g_col2, g_col3 = st.columns(3)

with g_col1:
    st.image(st.session_state.current_order[0], width=150)
with g_col2:
    st.image(st.session_state.current_order[1], width=150)
with g_col3:
    st.image(st.session_state.current_order[2], width=150)

st.divider()

# --- MAIN APP CONTENT ---
st.title("🎥 FFmpeg Command Generator")
st.markdown("Generate your FFmpeg strings quickly without managing spreadsheet rows.")

# --- COLUMN 1: INPUT CONFIGURATION ---
col1, col2, col3 = st.columns(3)

with col1:
    st.header("1. Input Source")
    input_host = st.text_input(
        "Input Host/IP", 
        value="54.156.246.82",
        help="The IP address of the source stream."
    )
    input_port = st.text_input(
        "Input Port", 
        value="37301",
        help="The port on the source server to connect to."
    )
    
    # Latency Logic
    add_latency = st.checkbox("Add latency?", value=True)
    latency_ms = 400
    if add_latency:
        latency_ms = st.number_input(
            "Latency (ms)", 
            value=400,
            help="SRT latency buffer. Higher values reduce packet loss but increase delay."
        )
        
    # Passphrase Logic
    add_passphrase = st.checkbox("Add passphrase?", value=True)
    passphrase = ""
    if add_passphrase:
        passphrase = st.text_input(
            "Passphrase", 
            value="ch301_wsc_y84fmq1",
            help="SRT connection security key."
        )

# --- COLUMN 2: ENCODING SETTINGS ---
with col2:
    st.header("2. Encoding")
    should_convert = st.checkbox("Convert video? (Not copy)", value=True)
    
    # Defaults
    yadif_mode = 1
    maxrate = 15000000
    fps_val = "30000/1001"
    
    if should_convert:
        is_interlaced = st.checkbox(
            "Is interlaced?", 
            value=True,
            help="Check this if the source video is interlaced (e.g., 1080i) and needs deinterlacing."
        )
        if is_interlaced:
            yadif_mode = st.selectbox(
                "YADIF Mode", 
                [0, 1], 
                index=1, 
                help="0: One frame for each frame (keep FPS).\n1: One frame for each field (Double FPS)."
            )
            
        st.caption("Video Parameters")
        maxrate = st.number_input(
            "Maxrate (bps)", 
            value=15000000,
            help="Maximum bitrate limit for the encoder."
        )
        fps_val = st.text_input(
            "FPS Value", 
            value="30000/1001",
            help="Frame rate fraction (e.g., 30000/1001 for 29.97 fps)."
        )
        gop_val = st.number_input(
            "GOP Value", 
            value=50,
            help="Group of Pictures size. Determines keyframe interval."
        )
        
        st.caption("Audio Parameters")
        audio_codec = st.text_input("Audio Codec", value="aac")
        audio_bitrate = st.text_input("Audio Bitrate", value="192k")

# --- COLUMN 3: OUTPUT & CONFIG ---
with col3:
    st.header("3. Channel & Output")
    
    # --- NEW CHANNEL CONFIG ---
    st.markdown("##### 📝 Channel Identity")
    channel_name = st.text_input("Channel Name", value="nbcchannel6")
    
    # Static IP Checkbox
    use_static_ip = st.checkbox(
        "Static IP", 
        value=True,
        help="Check this when using whitelisting with the customer."
    )
    
    st.divider()
    
    # --- EXISTING WOWZA CONFIG ---
    st.markdown("##### 📡 Destination")
    wowza_server = st.number_input(
        "Wowza Server Number", 
        value=21, 
        step=1,
        help="This number changes the output URL (e.g. wsc-wowza21...)"
    )
    wowza_port = st.number_input(
        "Wowza Port", 
        value=10011,
        help="Destination port on the Wowza server."
    )
    output_timeout = st.number_input(
        "Output Timeout (ms)", 
        value=10000000,
        help="Connection timeout for the output SRT stream."
    )

# --- GENERATE COMMAND LOGIC ---
st.divider()

# Build Input SRT
srt_input = f"srt://{input_host}:{input_port}?fc=5000000&rcvbuf=100000000&timeout=10000000"
if add_latency:
    srt_input += f"&latency={latency_ms}"
if add_passphrase:
    srt_input += f"&passphrase={passphrase}"

# Build Output SRT
output_url = f"srt://wsc-wowza{wowza_server}-prod-wowza-eus2.eastus2.cloudapp.azure.com:{wowza_port}?timeout={output_timeout}"

# Build Video Flags
video_flags = ""
if should_convert:
    # Interlaced filter
    if is_interlaced:
        video_flags += f" -vf yadif=mode={yadif_mode}"
    
    # Encoding block from sheet
    video_flags += " -vcodec h264_nvenc -s 1920x1080 -rc:v vbr -cq:v 20 -pix_fmt yuv420p -f mpegts"
    
    # Audio block
    video_flags += f" -acodec {audio_codec} -b:a {audio_bitrate}"
    
    # Mapping block
    video_flags += " -map v:0 -map a:0?"
    video_flags += " -streamid 0:0x100 -streamid 1:0x101"

# Build final FFmpeg string (Value only)
ffmpeg_value = (
    f"-timeout 20000000 -rw_timeout 20000000 "
    f"-i {srt_input}"
    f"{video_flags} "
    f"{output_url}"
)

# Build YAML Output
final_yaml = f"""- name: {channel_name}
  staticip: {str(use_static_ip).lower()}
  ffmpegcommand: {ffmpeg_value}"""

st.subheader("Generated YAML Configuration")
st.code(final_yaml, language="yaml")