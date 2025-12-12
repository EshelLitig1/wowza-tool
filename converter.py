import streamlit as st

st.set_page_config(page_title="Wowza Interlaced Converter", layout="wide")

st.title("🎥 FFmpeg Command Generator")
st.markdown("Generate your FFmpeg strings quickly without managing spreadsheet rows.")

# --- COLUMN 1: INPUT CONFIGURATION ---
col1, col2, col3 = st.columns(3)

with col1:
    st.header("1. Input Source")
    input_host = st.text_input("Input Host/IP", value="54.156.246.82")
    input_port = st.text_input("Input Port", value="37301")
    
    # Latency Logic
    add_latency = st.checkbox("Add latency?", value=True)
    latency_ms = 400
    if add_latency:
        latency_ms = st.number_input("Latency (ms)", value=400)
        
    # Passphrase Logic
    add_passphrase = st.checkbox("Add passphrase?", value=True)
    passphrase = ""
    if add_passphrase:
        passphrase = st.text_input("Passphrase", value="ch301_wsc_y84fmq1")

# --- COLUMN 2: ENCODING SETTINGS ---
with col2:
    st.header("2. Encoding")
    should_convert = st.checkbox("Convert video? (Not copy)", value=True)
    
    # Defaults
    yadif_mode = 1
    maxrate = 15000000
    fps_val = "30000/1001"
    
    if should_convert:
        is_interlaced = st.checkbox("Is interlaced?", value=True)
        if is_interlaced:
            yadif_mode = st.selectbox("YADIF Mode", [0, 1], index=1, help="0: keep FPS, 1: double FPS")
            
        st.caption("Video Parameters")
        maxrate = st.number_input("Maxrate (bps)", value=15000000)
        fps_val = st.text_input("FPS Value", value="30000/1001")
        gop_val = st.number_input("GOP Value", value=50)
        
        st.caption("Audio Parameters")
        audio_codec = st.text_input("Audio Codec", value="aac")
        audio_bitrate = st.text_input("Audio Bitrate", value="192k")

# --- COLUMN 3: OUTPUT TARGET ---
with col3:
    st.header("3. Output Target")
    wowza_server = st.number_input("Wowza Server Number", value=21, step=1)
    wowza_port = st.number_input("Wowza Port", value=10011)
    output_timeout = st.number_input("Output Timeout (ms)", value=10000000)

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

# Final Assembly
final_cmd = (
    f"ffmpegcommand: -timeout 20000000 -rw_timeout 20000000 "
    f"-i {srt_input}"
    f"{video_flags} "
    f"{output_url}"
)

st.subheader("Generated Command")
st.code(final_cmd, language="bash")