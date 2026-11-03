import json
import re

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Wowza Interlaced Converter", layout="wide")

STATIC_IP = "20.98.207.73"


def _ip_with_copy_button(ip: str) -> None:
    """Renders the IP text and the copy icon right next to each other, with no gap."""
    components.html(
        f"""
        <body style="margin:0; padding:0; background:transparent; overflow:visible;">
            <div style="display:flex; align-items:center; gap:3px; height:32px;">
                <span style="color:#9ca3af; font-size:0.875rem; white-space:nowrap;">{ip}</span>
                <button title="Copy to clipboard"
                        onclick="navigator.clipboard.writeText('{ip}'); this.style.opacity='0.4'; setTimeout(() => this.style.opacity='1', 800);"
                        style="padding:0; border:none; background:transparent; cursor:pointer; color:#9ca3af; line-height:0; display:flex; align-items:center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                </button>
            </div>
        </body>
        """,
        height=32,
    )

# --- ENCODESPECS HELPERS ---
CPU_MODES = ["Caller", "Listener"]  # CPU nodes always copy the video
TRACK_MODES = [
    "Default (first track + up to 7 optional)",
    "Custom list",
    "No audio",
    "Auto (ffmpeg picks one track)",
]
DATA_MODES = ["Default (first data track, optional)", "None (drop data tracks)", "Custom list"]
OUTPUT_TRACK_TYPES = ["Input track", "Input track (optional)", "PID", "PID (optional)", "Named selector", "Mix"]
MIX_CHANNELS = ["L", "R", "C", "LFE", "Ls", "Rs"] + [str(n) for n in range(8)]


def _pick(label, options, key, help=None, default_label="Default"):
    """Selectbox whose first entry means 'do not write this field'. Returns None for that entry."""
    choice = st.selectbox(label, [default_label] + list(options), key=key, help=help)
    return None if choice == default_label else choice


def _num_or_str(text):
    text = str(text).strip()
    return int(text) if text.isdigit() else text


def _gain(value):
    return int(value) if float(value).is_integer() else float(value)


def _validated_text(label, key, placeholder, pattern, hint, problems, help=None):
    """Text input that stays empty = 'default'. Appends to problems when the value has a wrong format."""
    value = st.text_input(label, key=key, placeholder=placeholder, help=help).strip()
    if value and not re.fullmatch(pattern, value, re.IGNORECASE):
        problems.append(f"{label}: '{value}' is not valid ({hint})")
        return ""
    return value


def _parse_track_items(text, problems, label):
    """'0, 1?, pid:257, pid:258?' -> [0, "1?", {"pid": 257}, {"pid": 258, "optional": True}]"""
    items = []
    for raw in [p.strip() for p in text.split(",") if p.strip()]:
        optional = raw.endswith("?")
        core = raw[:-1].strip() if optional else raw
        if core.lower().startswith("pid:") and core[4:].strip().isdigit():
            item = {"pid": int(core[4:].strip())}
            if optional:
                item["optional"] = True
            items.append(item)
        elif core.isdigit():
            items.append(f"{core}?" if optional else int(core))
        else:
            problems.append(f"{label}: '{raw}' is not valid (use 0, 1?, pid:257 or pid:257?)")
    return items


def _parse_mix_side(text, selectors, label, problems):
    """'a1.L:1, a2.R:0.5' -> {"a1.L": 1, "a2.R": 0.5}"""
    side = {}
    for raw in [p.strip() for p in text.split(",") if p.strip()]:
        ref, _, gain_text = raw.partition(":")
        ref = ref.strip()
        sel_name, _, channel = ref.partition(".")
        gain = 1
        if gain_text.strip():
            try:
                gain = _gain(float(gain_text))
            except ValueError:
                problems.append(f"{label}: gain '{gain_text.strip()}' is not a number")
                continue
            if gain < 0:
                problems.append(f"{label}: gain can't be negative")
                continue
        if sel_name not in selectors:
            problems.append(f"{label}: '{sel_name}' is not a defined selector")
            continue
        if selectors[sel_name].get("optional"):
            problems.append(f"{label}: selector '{sel_name}' is optional, a mix needs its tracks")
            continue
        if channel not in MIX_CHANNELS:
            problems.append(f"{label}: channel '{channel}' is not valid (L, R, C, LFE, Ls, Rs or 0-7)")
            continue
        side[ref] = gain
    if not side and not text.strip():
        problems.append(f"{label}: enter at least one input, e.g. a1.L:1")
    return side

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
app_mode = st.selectbox(
    "Select Mode",
    ["Caller (encoding)", "Caller", "Listener (encoding)", "Listener", "RTMP pull"],
)

MODE_INFO = (
    "There is no need for a Wowza stream file. Just fill in all relevant fields bellow and then copy "
    'the "YAML Configuration" result to the relevant YAML URL. The pod automation is being added automatically. '
    "The HLS Playlist Preview holds the ready to use HLS"
)
if app_mode in ["Caller (encoding)", "Caller", "Listener (encoding)", "Listener", "RTMP pull"]:
    st.info(MODE_INFO)

if app_mode in ["Caller (encoding)", "RTMP pull"]:
    repo_urls = ["https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-gpu/values.yaml"]
elif app_mode == "Caller":
    repo_urls = ["https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-cpu/values.yaml"]
elif app_mode == "Listener":
    repo_urls = [
        "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-cpu-listeners/values.yaml",
        "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-cpu-listeners2/values.yaml",
        "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-cpu-listeners3/values.yaml",
    ]
else:
    repo_urls = [
        "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-gpu-listeners/values.yaml",
        "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-gpu-listeners2/values.yaml",
        "https://github.com/WSCSportsEngineering/mediaservices-values/blob/main/wsc-ffmpeg-gpu-listeners3/values.yaml",
    ]

endpoint_count = int(
    st.number_input(
        "Number of endpoints",
        min_value=1,
        value=1,
        step=1,
        help="For multiple endpoints, the YAML and HLS preview output will include one entry per endpoint.",
    )
)

col1, col2, col3 = st.columns(3)

# --- 1. INPUT SOURCE ---
with col1:
    st.header("1. Input Source")
    endpoints = []

    if app_mode == "RTMP pull":
        add_passphrase = False
        has_static_ip = False

        for i in range(endpoint_count):
            container = st.expander(f"Endpoint {i + 1}", expanded=True) if endpoint_count > 1 else st.container()
            with container:
                pull_url = st.text_input(
                    "Complete RTMP pull URL",
                    value="",
                    key=f"rtmp_pull_url_{i}",
                )
                st.caption("Example: rtmp://125.212.235.78:1935/live/livestream01_xJXA04ny0he0SlbJeeXOBHl0")
                endpoints.append({"url": pull_url})
    elif app_mode in ["Caller (encoding)", "Caller"]:
        add_passphrase = st.checkbox("Add passphrase?", value=False)
        static_check_col, static_ip_col = st.columns(
            [0.55, 1.45], gap="small", vertical_alignment="center"
        )
        with static_check_col:
            has_static_ip = st.checkbox("Static IP")
        with static_ip_col:
            _ip_with_copy_button(STATIC_IP)

        for i in range(endpoint_count):
            container = st.expander(f"Endpoint {i + 1}", expanded=True) if endpoint_count > 1 else st.container()
            with container:
                input_host = st.text_input(
                    "Input Host/IP",
                    value="54.156.246.82" if i == 0 else "",
                    key=f"input_host_{i}",
                )
                input_port = st.text_input(
                    "Input Port",
                    value=str(37301 + i),
                    key=f"input_port_{i}",
                )
                endpoint_passphrase = (
                    st.text_input("Passphrase", value="ch301_wsc_y84fmq1", key=f"passphrase_{i}")
                    if add_passphrase
                    else ""
                )
                endpoints.append({"host": input_host, "port": input_port, "passphrase": endpoint_passphrase})
    else:
        st.info("go to the YAML URL and find the next available port from the 'clusterportin' field")
        st.info("IP can be found in the choosen YAML")
        add_passphrase = st.checkbox("Add passphrase?", value=False)
        has_static_ip = False

        for i in range(endpoint_count):
            container = st.expander(f"Endpoint {i + 1}", expanded=True) if endpoint_count > 1 else st.container()
            with container:
                input_port = st.text_input(
                    "Input Port",
                    value=str(37301 + i),
                    key=f"listener_input_port_{i}",
                )
                endpoint_passphrase = (
                    st.text_input("Passphrase", value="ch301_wsc_y84fmq1", key=f"listener_passphrase_{i}")
                    if add_passphrase
                    else ""
                )
                endpoints.append({"host": "", "port": input_port, "passphrase": endpoint_passphrase})

# --- 2. ENCODING SETTINGS (encodespecs) ---
with col2:
    st.header("2. Encoding")

    spec_problems = []
    is_cpu_mode = app_mode in CPU_MODES
    video_spec = {}
    decode_choice = None

    # ---- Video ----
    if is_cpu_mode:
        force_encode_video = st.checkbox(
            "Force encode video",
            value=False,
            disabled=True,
            help="This mode runs on a CPU node, which always copies the video. Video encoding is not available here.",
        )
        st.caption("CPU node: the video is always copied.")
    else:
        force_encode_video = st.checkbox(
            "Force encode video",
            value=False,
            help="By default the wrapper inspects the stream and converts it to the default specs by itself. "
            "Check this to set the video encoding options manually.",
        )

    if force_encode_video:
        st.markdown(
            "For more info refer to this "
            "[guide](https://docs.google.com/document/d/1AFLuUBL1dDFA31sCulWO_CjsuQtZsD6jLtZQ1Raiw6s/edit?tab=t.0)"
        )
        st.caption(
            "Every field you set here is pinned: the wrapper never changes it automatically "
            "and only logs a warning if the input disagrees. Leave a field on Default to let the wrapper decide."
        )
        decode_choice = _pick(
            "Decode",
            ["gpu", "cpu"],
            key="enc_decode",
            default_label="Default (gpu)",
            help="Where the video is decoded before encoding. The wrapper falls back to CPU by itself "
            "when the GPU can't decode the input.",
        )

        fps_choice = _pick(
            "FPS",
            ["25", "30", "50", "60", "30000/1001", "60000/1001", "Custom"],
            key="enc_fps",
            default_label="Default (50, then learned from input)",
            help='29.97 / 59.94 are written as "30000/1001" / "60000/1001".',
        )
        if fps_choice == "Custom":
            fps_custom = _validated_text(
                "Custom FPS", "enc_fps_custom", "e.g. 24 or 24000/1001", r"\d+(/\d+)?", "a number or a fraction",
                spec_problems,
            )
            if fps_custom:
                video_spec["fps"] = _num_or_str(fps_custom)
        elif fps_choice:
            video_spec["fps"] = _num_or_str(fps_choice)

        size_text = _validated_text(
            "Size", "enc_size", "Default 1920x1080", r"\d+x\d+|source", 'WxH like 1920x1080, or "source"',
            spec_problems, help='Output resolution. "source" keeps the input size.',
        )
        if size_text:
            video_spec["size"] = size_text.lower()

        sar_text = _validated_text(
            "SAR (pixel aspect ratio)", "enc_sar", "Default 1:1", r"\d+:\d+", "A:B like 1:1", spec_problems
        )
        if sar_text:
            video_spec["sar"] = sar_text

        dar_text = _validated_text(
            "DAR (display aspect ratio)", "enc_dar", "Default 16:9", r"\d+:\d+", "A:B like 16:9", spec_problems
        )
        if dar_text:
            video_spec["dar"] = dar_text

        gop_text = _validated_text(
            "GOP", "enc_gop", "Default 1s", r"\d+s?", "like 1s, 2s or a frame count", spec_problems,
            help="Keyframe interval: 1s, 2s or a frame count.",
        )
        if gop_text:
            video_spec["gop"] = _num_or_str(gop_text.lower())

        rate_bps = st.number_input(
            "Max bitrate",
            min_value=1,
            value=None,
            step=1,
            placeholder="Default 15000000",
            key="enc_rate_bps",
            help="Written as-is (bps, e.g. 20000000). The rate setting is only written when a bitrate is set.",
        )
        if rate_bps:
            rate_mode = st.selectbox(
                "Rate mode",
                ["VBR + quality (CQ)", "VBR (bitrate cap only)", "CBR"],
                key="enc_rate_mode",
            )
            if rate_mode == "VBR + quality (CQ)":
                rate_cq = int(
                    st.number_input(
                        "Quality level (CQ)",
                        min_value=0,
                        max_value=51,
                        value=18,
                        step=1,
                        key="enc_rate_cq",
                        help="0-51, lower is better.",
                    )
                )
                video_spec["rate"] = f"{int(rate_bps)},{rate_cq}"
            elif rate_mode == "CBR":
                video_spec["rate"] = f"{int(rate_bps)}cbr"
            else:
                video_spec["rate"] = f"{int(rate_bps)}"

        preset_choice = _pick(
            "Preset",
            [f"p{n}" for n in range(1, 8)],
            key="enc_preset",
            default_label="Default (p3)",
            help="NVENC speed/quality: p1 fastest, p7 best.",
        )
        if preset_choice:
            video_spec["preset"] = preset_choice

        const_gop_choice = _pick(
            "Constant GOP",
            ["true", "false"],
            key="enc_const_gop",
            default_label="Default (false)",
            help="true: keyframes only every GOP, no extra ones at scene cuts.",
        )
        if const_gop_choice:
            video_spec["constantGop"] = const_gop_choice == "true"

        deinterlace_choice = _pick(
            "Deinterlace",
            ["none", "frame", "framedouble"],
            key="enc_deinterlace",
            default_label="Default (none, then learned from input)",
            help='"framedouble" outputs one frame per field (25i -> 50p).',
        )
        if deinterlace_choice:
            video_spec["deinterlace"] = deinterlace_choice
    elif not is_cpu_mode:
        max_bitrate = st.number_input(
            "Max bitrate",
            min_value=1,
            value=None,
            step=1,
            placeholder="e.g. 20000000",
            key="enc_max_bitrate",
            help="Written as-is (bps, e.g. 20000000). Leave empty to keep the wrapper default.",
        )
        st.info("specify if more than 15 MB/s")
        if max_bitrate:
            video_spec["rate"] = f"{int(max_bitrate)},18"

    # ---- Audio ----
    st.divider()
    st.subheader("Audio")

    audio_encode_choice = _pick(
        "Audio encode",
        ["Force encode to AAC stereo", "Force copy"],
        key="enc_audio_encode",
        default_label="Default (wrapper decides)",
        help="Default: encoded on GPU nodes, when a mix is used, or when a selected track is AC-3/E-AC-3; "
        "otherwise copied.",
    )
    audio_encode = None if audio_encode_choice is None else audio_encode_choice.startswith("Force encode")

    audio_bitrate = _validated_text(
        "Audio bitrate", "enc_audio_bitrate", "Default 192k", r"\d+[km]?", "like 128k, 192k or 256k", spec_problems,
        help="AAC bitrate per track. Only applies when the audio is encoded.",
    )
    sample_rate = _pick(
        "Sample rate", ["48000", "44100"], key="enc_sample_rate", default_label="Default (48000)",
        help="Only applies when the audio is encoded.",
    )
    audio_spec = {}
    if audio_bitrate:
        audio_spec["bitrate"] = audio_bitrate.lower()
    if sample_rate:
        audio_spec["sampleRate"] = int(sample_rate)

    if app_mode == "Listener":
        is_multi_audio = st.checkbox(
            "Is multi audio",
            value=True,
            disabled=True,
            help="For this mode there is no need to configure multi audio. It works by default.",
        )
    else:
        is_multi_audio = st.checkbox(
            "Is multi audio", value=False, help="Adds outputhls_multiple_audio_count: auto to the YAML."
        )

    tracks_audio = None
    tracks_selectors = None
    tracks_data = None
    mix_used = False

    with st.expander("Audio tracks & mixes"):
        tracks_mode = st.selectbox("Output audio tracks", TRACK_MODES, key="enc_tracks_mode")

        if tracks_mode == "Custom list":
            st.caption("A custom list replaces the 8 default outputs completely.")
            selectors = {}
            selector_specs = []
            n_sel = int(
                st.number_input(
                    "Named input tracks (selectors)",
                    min_value=0,
                    value=0,
                    step=1,
                    key="enc_n_sel",
                    help="Needed for mixes and for 'Named selector' outputs.",
                )
            )
            for s in range(n_sel):
                c_name, c_kind, c_val = st.columns([1.3, 1, 1])
                sel_name = c_name.text_input(f"Selector {s + 1}", value=f"a{s + 1}", key=f"enc_sel_name_{s}").strip()
                sel_kind = c_kind.selectbox("Input by", ["track", "pid", "stream"], key=f"enc_sel_kind_{s}")
                sel_val = int(c_val.number_input("Value", min_value=0, value=s, step=1, key=f"enc_sel_val_{s}"))
                sel_optional = st.checkbox("Optional (skip if missing)", key=f"enc_sel_opt_{s}")
                if not re.fullmatch(r"[a-z0-9_]+", sel_name):
                    spec_problems.append(f"Selector {s + 1}: the name must be lowercase letters, digits and _")
                elif sel_name in selectors:
                    spec_problems.append(f"Selector {s + 1}: the name '{sel_name}' is used twice")
                else:
                    sel_spec = {"name": sel_name, sel_kind: sel_val}
                    if sel_optional:
                        sel_spec["optional"] = True
                    selectors[sel_name] = sel_spec
                    selector_specs.append(sel_spec)

            n_out = int(
                st.number_input(
                    "Number of output audio tracks", min_value=1, value=1, step=1, key="enc_n_out"
                )
            )
            outputs = []
            for t in range(n_out):
                out_label = f"Output track {t + 1}"
                st.markdown(f"**{out_label}**")
                out_type = st.selectbox("Type", OUTPUT_TRACK_TYPES, key=f"enc_out_type_{t}")
                if out_type in ("Input track", "Input track (optional)"):
                    track_no = int(
                        st.number_input(
                            "Input track number (0 = first)", min_value=0, value=t, step=1, key=f"enc_out_track_{t}"
                        )
                    )
                    outputs.append(f"{track_no}?" if out_type.endswith("(optional)") else track_no)
                elif out_type in ("PID", "PID (optional)"):
                    pid_value = st.number_input(
                        "MPEG-TS PID", min_value=0, value=None, step=1, placeholder="e.g. 257", key=f"enc_out_pid_{t}"
                    )
                    if pid_value is None:
                        spec_problems.append(f"{out_label}: enter a PID")
                    else:
                        pid_item = {"pid": int(pid_value)}
                        if out_type.endswith("(optional)"):
                            pid_item["optional"] = True
                        outputs.append(pid_item)
                elif out_type == "Named selector":
                    if not selectors:
                        spec_problems.append(f"{out_label}: define a selector first")
                    else:
                        chosen = st.selectbox("Selector", list(selectors), key=f"enc_out_sel_{t}")
                        outputs.append({"selector": chosen})
                else:
                    mix_used = True
                    st.caption(
                        "Format: selector.channel:gain, ... e.g. a1.L:1 or main.L:1, comm.L:0.5. "
                        "Channels: L, R, C, LFE, Ls, Rs or 0-7. Gain 1 = full level, 0.5 = half."
                    )
                    sides = st.selectbox("Output sides", ["L / R", "0 / 1"], key=f"enc_mix_sides_{t}")
                    left_key, right_key = ("L", "R") if sides == "L / R" else ("0", "1")
                    left_text = st.text_input(
                        "Left side inputs", key=f"enc_mix_left_{t}", placeholder="a1.L:1"
                    )
                    right_text = st.text_input(
                        "Right side inputs", key=f"enc_mix_right_{t}", placeholder="a1.L:1"
                    )
                    left = _parse_mix_side(left_text, selectors, f"{out_label} left", spec_problems)
                    right = _parse_mix_side(right_text, selectors, f"{out_label} right", spec_problems)
                    if left and right:
                        outputs.append({"mix": {left_key: left, right_key: right}})
            tracks_audio = outputs
            tracks_selectors = selector_specs or None
        elif tracks_mode == "No audio":
            tracks_audio = []
        elif tracks_mode == TRACK_MODES[3]:
            tracks_audio = "auto"

        if tracks_mode == TRACK_MODES[3]:
            st.caption('Data tracks are set to none, which "auto" requires.')
            tracks_data = []
        else:
            data_mode = st.selectbox("Data tracks (SCTE-35, VANC)", DATA_MODES, key="enc_data_mode")
            if data_mode == DATA_MODES[1]:
                tracks_data = []
            elif data_mode == DATA_MODES[2]:
                data_text = st.text_input(
                    "Data tracks list",
                    key="enc_data_list",
                    placeholder="0?",
                    help="Comma-separated, same format as audio: 0, 1?, pid:257?",
                )
                tracks_data = _parse_track_items(data_text, spec_problems, "Data tracks")
                if not data_text.strip():
                    spec_problems.append("Data tracks: enter at least one track, or choose None")

    if mix_used and audio_encode is False:
        spec_problems.append("A mix is always encoded: 'Audio encode' can't be 'Force copy' together with a mix")

    # ---- Advanced ----
    tracks_video = None
    with st.expander("Advanced"):
        video_track_type = _pick(
            "Input video stream",
            ["Track index", "PID", "Stream"],
            key="enc_vtrack_type",
            default_label="Default (0)",
        )
        if video_track_type:
            video_track_value = int(
                st.number_input("Value", min_value=0, value=0, step=1, key="enc_vtrack_val")
            )
            if video_track_type == "Track index":
                tracks_video = video_track_value
            elif video_track_type == "PID":
                tracks_video = {"pid": video_track_value}
            else:
                tracks_video = {"stream": video_track_value}
        extra_args = st.text_input(
            "Extra args",
            key="enc_extra_args",
            help="Extra ffmpeg options added at the end, unchanged. Last resort only.",
        ).strip()

    # ---- Build the encodespecs object (only the fields that were set) ----
    tracks_spec = {}
    if tracks_video is not None:
        tracks_spec["video"] = tracks_video
    if tracks_selectors:
        tracks_spec["audioSelectors"] = tracks_selectors
    if tracks_audio is not None:
        tracks_spec["audio"] = tracks_audio
    if tracks_data is not None:
        tracks_spec["data"] = tracks_data

    encode_spec = {}
    if force_encode_video:
        encode_spec["encode"] = True
    if audio_encode is not None:
        encode_spec["audioEncode"] = audio_encode
    if decode_choice:
        encode_spec["decode"] = decode_choice
    if video_spec:
        encode_spec["video"] = video_spec
    if audio_spec:
        encode_spec["audio"] = audio_spec
    if tracks_spec:
        encode_spec["tracks"] = tracks_spec
    if extra_args:
        encode_spec["extraArgs"] = extra_args

# --- 3. OUTPUT PATH & INFO ---
with col3:
    st.header("3. Output Path")
    app_name = st.text_input("Application name", value="live")
    stream_name_label = "Base stream file name" if endpoint_count > 1 else "Stream file name"
    stream_name = st.text_input(stream_name_label, value="stream")
    if endpoint_count > 1:
        st.caption(f"Generated stream names: {stream_name}1 through {stream_name}{endpoint_count}")
    
    st.divider()
    st.caption("Tagging Info")
    tam = st.text_input("TAM", value="")
    customer_id = st.number_input("Customer ID", value=0, step=1)
    reason = st.text_input("Reason", value="General Encoding")
    
    missing_fields = []
    if not app_name:
        missing_fields.append("Application name")
    if not stream_name:
        missing_fields.append("Stream file name")
    if not tam:
        missing_fields.append("TAM")

    if app_mode == "RTMP pull":
        for i, endpoint in enumerate(endpoints):
            if not endpoint["url"]:
                missing_fields.append(f"Endpoint {i + 1} RTMP pull URL")
    elif app_mode in ["Caller (encoding)", "Caller"]:
        for i, endpoint in enumerate(endpoints):
            if not endpoint["host"]:
                missing_fields.append(f"Endpoint {i + 1} input host/IP")
            if not endpoint["port"]:
                missing_fields.append(f"Endpoint {i + 1} input port")
    else:
        for i, endpoint in enumerate(endpoints):
            if not endpoint["port"]:
                missing_fields.append(f"Endpoint {i + 1} input port")

    valid_input = not missing_fields and not spec_problems

# --- GENERATE COMMAND LOGIC ---
st.divider()

if valid_input:
    # YAML single-quoted scalar: the JSON keeps its double quotes, a single quote is doubled
    encodespecs_line = (
        "  encodespecs: '" + json.dumps(encode_spec).replace("'", "''") + "'" if encode_spec else None
    )

    out_col1, out_col2 = st.columns(2)
    with out_col1:
        st.subheader("📄 YAML Configuration")
        if len(repo_urls) == 1:
            st.markdown(f"🔗 **YAML URL:** [{repo_urls[0]}]({repo_urls[0]})")
        else:
            st.markdown("🔗 **YAML URLs:**")
            for idx, url in enumerate(repo_urls, start=1):
                st.markdown(f"URL{idx}: [{url}]({url})")
        
        # Build info comment
        info_dict = {"TAM": tam, "Customer ID": str(customer_id), "Reason": reason}
        info_row = f"  #{json.dumps(info_dict)}"
        
        yaml_lines = []
        hls_preview_urls = []

        for i, endpoint in enumerate(endpoints):
            endpoint_stream_name = stream_name if endpoint_count == 1 else f"{stream_name}{i + 1}"

            if app_mode == "RTMP pull":
                srt_input = endpoint["url"]
            elif app_mode in ["Caller (encoding)", "Caller"]:
                srt_input = f"srt://{endpoint['host']}:{endpoint['port']}"
                if add_passphrase and endpoint.get("passphrase"):
                    srt_input += f"?passphrase={endpoint['passphrase']}"
            else:
                srt_input = f"srt://0.0.0.0:{endpoint['port']}"
                if add_passphrase and endpoint.get("passphrase"):
                    srt_input += f"?passphrase={endpoint['passphrase']}"

            yaml_lines.extend(
                [
                    f"- name: {endpoint_stream_name}",
                    info_row,
                ]
            )
            
            if app_mode in ["Listener (encoding)", "Listener"]:
                yaml_lines.append(f"  clusterportin: {endpoint['port']}")
                
            if has_static_ip:
                yaml_lines.append("  staticip: true")
                
            yaml_lines.append(f"  input: {srt_input}")
            
            if encodespecs_line:
                yaml_lines.append(encodespecs_line)
                
            yaml_lines.append(f"  outputhls_path: hls/{app_name}/{endpoint_stream_name}")
            
            if is_multi_audio:
                yaml_lines.append("  outputhls_multiple_audio_count: auto")

            # Keep user's manual URL structure
            hls_preview_urls.append(
                f"https://wowzaprodeus2.blob.core.windows.net/streams/hls/{app_name}/{endpoint_stream_name}/stream.m3u8"
            )
            
        st.code("\n".join(yaml_lines), language="yaml")
    
    with out_col2:
        st.subheader("🔗 HLS Playlist Preview")
        st.code("\n".join(hls_preview_urls), language="text")



else:
    if missing_fields:
        st.warning(f"⚠️ Please provide: {', '.join(missing_fields)}.")
    if spec_problems:
        st.error("⚠️ Fix the encoding options:\n\n" + "\n".join(f"- {p}" for p in spec_problems))
