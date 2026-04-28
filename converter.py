import streamlit as st
import json

st.set_page_config(page_title="Wowza Interlaced Converter", layout="wide")

# --- 🔄 RESET LOGIC ---
if st.sidebar.button("Sweep 🧹 Clear All Fields"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 🎮 MINI GAME (TIC-TAC-TOE) ---
st.sidebar.markdown("### Mini game: Tic‑Tac‑Toe")

if "ttt_board" not in st.session_state:
    st.session_state.ttt_board = [""] * 9
if "ttt_player" not in st.session_state:
    st.session_state.ttt_player = "X"
if "ttt_status" not in st.session_state:
    st.session_state.ttt_status = ""


def _ttt_winner(board: list[str]) -> str | None:
    wins = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]
    for a, b, c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def _ttt_play(idx: int) -> None:
    if st.session_state.ttt_status:
        return
    if st.session_state.ttt_board[idx]:
        return
    st.session_state.ttt_board[idx] = st.session_state.ttt_player
    winner = _ttt_winner(st.session_state.ttt_board)
    if winner:
        st.session_state.ttt_status = f"{winner} won!"
        return
    if all(st.session_state.ttt_board):
        st.session_state.ttt_status = "Draw!"
        return
    st.session_state.ttt_player = "O" if st.session_state.ttt_player == "X" else "X"


g1, g2, g3 = st.sidebar.columns(3)
for i in range(9):
    col = (g1, g2, g3)[i % 3]
    label = st.session_state.ttt_board[i] or " "
    col.button(label, key=f"ttt_{i}", on_click=_ttt_play, args=(i,), use_container_width=True)

if st.session_state.ttt_status:
    st.sidebar.info(st.session_state.ttt_status)
else:
    st.sidebar.caption(f"Turn: {st.session_state.ttt_player}")

if st.sidebar.button("Reset Tic‑Tac‑Toe"):
    st.session_state.ttt_board = [""] * 9
    st.session_state.ttt_player = "X"
    st.session_state.ttt_status = ""

st.sidebar.divider()

# --- MAIN APP ---
st.title("🎥 FFmpeg Command Generator")
app_mode = st.selectbox("Select Mode", ["Caller (encoding)", "Caller", "Listener (encoding)", "Listener"])

if app_mode == "Listener":
    st.info("No need for FFMPEG. Use Wowza - http://wowza-dashboard.vibecoding.apps:3000 (enable the VPN)")
    st.stop()

MODE_INFO = (
    "There is no need for a Wowza stream file. Just fill in all relevant fields bellow and then copy "
    'the "YAML Configuration" result to the relevant YAML URL. The pod automation is being added automatically. '
    "The HLS Playlist Preview holds the ready to use HLS"
)
if app_mode in ["Caller (encoding)", "Caller", "Listener (encoding)"]:
    st.info(MODE_INFO)

if app_mode == "Caller (encoding)":
    repo_url = "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-gpu/values.yaml"
elif app_mode == "Caller":
    repo_url = "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-cpu/values.yaml"
else:
    repo_url = "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-gpu-listeners/values.yaml"

col1, col2, col3 = st.columns(3)

# --- 1. INPUT SOURCE ---
with col1:
    st.header("1. Input Source")
    if app_mode in ["Caller (encoding)", "Caller"]:
        input_host = st.text_input("Input Host/IP", value="54.156.246.82")
        input_port = st.text_input("Input Port", value="37301")
        add_passphrase = st.checkbox("Add passphrase?", value=True)
        passphrase = st.text_input("Passphrase", value="ch301_wsc_y84fmq1") if add_passphrase else ""
        has_static_ip = st.checkbox("Static IP :gray[- 20.98.207.73]")
    else:
        st.info("go to the YAML URL and find the next available port from the 'clusterportin' field")
        st.markdown("**Inbound IP:** 52.242.94.245")
        input_port = st.text_input("Input Port", value="37301")
        input_host = ""
        add_passphrase = False
        passphrase = ""
        has_static_ip = False

# --- 2. ENCODING SETTINGS ---
with col2:
    st.header("2. Encoding")
    
    if app_mode == "Caller":
        should_encode_video = st.checkbox("Encode video?", value=False, disabled=True, help="Video encoding is disabled in this mode")
    else:
        should_encode_video = st.checkbox("Encode video?", value=True, help="Uncheck if the video doesn't need to be converted")
    
    if should_encode_video:
        is_interlaced = st.checkbox("Is interlaced?", value=True)
        bwdif_mode = 1
        if is_interlaced:
            bwdif_mode = st.selectbox("BWDIF/YADIF Mode", options=[0, 1], index=1, help="Mode 0: Standard frame rate. Mode 1: Double frame rate.")
        fps_selection = st.selectbox("FPS Value", options=["60", "60000/1001", "30", "30000/1001", "50", "25"], index=3)
    
    st.divider()
    if app_mode == "Caller":
        should_encode_audio = st.checkbox("Encode audio?", value=False, help="Audio encoding disabled by default in this mode")
    else:
        should_encode_audio = st.checkbox("Encode audio?", value=True)
    is_multi_audio = st.checkbox("Is multi audio", value=False)
    num_audio_tracks = 1
    if is_multi_audio:
        num_audio_tracks = st.number_input("Num of stereo tracks", min_value=1, value=2, step=1)
    audio_codec = st.text_input("Audio Codec", value="aac")
    audio_bitrate = st.text_input("Audio Bitrate", value="192k")

# --- 3. OUTPUT PATH & INFO ---
with col3:
    st.header("3. Output Path")
    app_name = st.text_input("Application name", value="live")
    stream_name = st.text_input("Stream file name", value="stream")
    
    st.divider()
    st.caption("Tagging Info")
    tam = st.text_input("TAM", value="")
    customer_id = st.number_input("Customer ID", value=0, step=1)
    reason = st.text_input("Reason", value="General Encoding")
    
    valid_input = bool(app_name and stream_name)

# --- GENERATE COMMAND LOGIC ---
st.divider()

if valid_input:
    if app_mode in ["Caller (encoding)", "Caller"]:
        srt_input = f"srt://{input_host}:{input_port}"
        if add_passphrase and passphrase:
            srt_input += f"?passphrase={passphrase}"
    else:
        srt_input = f"srt://0.0.0.0:{input_port}"

    cmd_parts = []
    
    # Custom format for 'Caller' mode with multi-audio
    if app_mode == "Caller" and is_multi_audio and not should_encode_video and not should_encode_audio:
        cmd_parts.append("-c copy")
        cmd_parts.append("-map v:0")
        for i in range(int(num_audio_tracks)):
            cmd_parts.append(f"-map a:{i}?")
    else:
        if should_encode_video:
            if is_interlaced: cmd_parts.append(f"-vf bwdif=mode={bwdif_mode}")
            gop_map = {"60":"60", "60000/1001":"60", "30":"30", "30000/1001":"30", "50":"50", "25":"25"}
            cmd_parts.append(f"-vcodec h264_nvenc -s 1920x1080 -rc:v vbr -cq:v 20 -maxrate 15000000 -pix_fmt yuv420p -r {fps_selection} -g {gop_map.get(fps_selection, '30')}")
        else:
            cmd_parts.append("-vcodec copy")

        if should_encode_audio:
            cmd_parts.append(f"-acodec {audio_codec} -b:a {audio_bitrate}")
        else:
            cmd_parts.append("-acodec copy")

        cmd_parts.append("-map v:0")
        for i in range(int(num_audio_tracks) if is_multi_audio else 1):
            audio_map = f"-map a:{i}?" if is_multi_audio else f"-map a:{i}"
            cmd_parts.append(audio_map)

    ffmpeg_value = " ".join(cmd_parts)
    
    # Keep user's manual URL structure
    hls_preview_url = f"https://wowzaprodeus2.blob.core.windows.net/streams/hls/{app_name}/{stream_name}/stream.m3u8"

    out_col1, out_col2 = st.columns(2)
    with out_col1:
        st.subheader("📄 YAML Configuration")
        st.markdown(f"🔗 **YAML URL:** [{repo_url}]({repo_url})")
        
        # Build info comment
        info_dict = {"TAM": tam, "Customer ID": str(customer_id), "Reason": reason}
        info_row = f"  #{json.dumps(info_dict)}"
        
        yaml_lines = [
            f"- name: {stream_name}",
            info_row,
        ]
        
        if app_mode == "Listener (encoding)":
            yaml_lines.append(f"  clusterportin: {input_port}")
            
        if has_static_ip:
            yaml_lines.append("  staticip: true")
            
        yaml_lines.append(f"  input: {srt_input}")
        
        if should_encode_video or should_encode_audio or (app_mode == "Caller" and is_multi_audio):
            yaml_lines.append(f"  ffmpegcommand: {ffmpeg_value}")
            
        yaml_lines.append(f"  outputhls_path: hls/{app_name}/{stream_name}")
        
        if is_multi_audio:
            yaml_lines.append("  outputhls_multiple_audio_count: auto")
            
        st.code("\n".join(yaml_lines), language="yaml")
    
    with out_col2:
        st.subheader("🔗 HLS Playlist Preview")
        st.code(hls_preview_url, language="text")



else:
    st.warning("⚠️ Please provide Application and Stream names.")
