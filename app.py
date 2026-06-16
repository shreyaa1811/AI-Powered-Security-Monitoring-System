import streamlit as st
import pandas as pd
from datetime import datetime
import random
from faker import Faker
import json, ast
import ollama
from streamlit_autorefresh import st_autorefresh
from pipeline.predict import predict
import altair as alt

#Displaying page settings
st.set_page_config(
    page_title="Security Monitoring System",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container { padding: 1.5rem 2rem 2rem; max-width: 1400px; }
[data-testid="stSidebar"] { padding-top: 1.5rem; }

.section-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #888780;
    margin: 0 0 10px;
    padding-bottom: 6px;
    border-bottom: 0.5px solid rgba(0,0,0,0.12);
}

.metric-row { display: flex; gap: 10px; margin-bottom: 1rem; }
.metric-card {
    flex: 1;
    background: rgba(0,0,0,0.03);
    border-radius: 8px;
    padding: 12px 14px;
    min-width: 0;
}
.metric-card .m-label { font-size: 11px; color: #888780; margin: 0 0 4px; white-space: nowrap; }
.metric-card .m-value { font-size: 22px; font-weight: 600; margin: 0; line-height: 1.1; }
.metric-card.attack .m-value { color: #E24B4A; }
.metric-card.safe  .m-value { color: #1D9E75; }
.metric-card.high  .m-value { color: #E24B4A; }

.badge { display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: 0.04em; padding: 2px 8px; border-radius: 4px; }
.badge-attack { background: #FCEBEB; color: #A32D2D; }
.badge-safe   { background: #EAF3DE; color: #3B6D11; }
.badge-high   { background: #FCEBEB; color: #A32D2D; }
.badge-medium { background: #FAEEDA; color: #854F0B; }
.badge-low    { background: #EAF3DE; color: #3B6D11; }

.explanation-box {
    background: rgba(0,0,0,0.02);
    border: 0.5px solid rgba(0,0,0,0.1);
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 13px;
    line-height: 1.65;
    margin-top: 8px;
}

.divider-label {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 1.25rem 0 0.75rem;
    color: #888780;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}
.divider-label::before, .divider-label::after {
    content: '';
    flex: 1;
    height: 0.5px;
    background: rgba(0,0,0,0.12);
}
</style>
""", unsafe_allow_html=True)

#Creating fake attack logs
faker = Faker()
attack_types = ["brute_force", "port_scan", "data_exfiltration"]

#Sidebar config
with st.sidebar:
    st.markdown("### Settings")
    st.caption("Configure live monitoring behaviour")
    interval = st.slider("Refresh interval (s)", 2, 10, 3)
    attack_prob = st.slider("Attack probability", 0.0, 1.0, 0.3, step=0.05)
    use_llm = st.checkbox("Use LLM analysis", value=False, help="Disable to keep dashboard responsive.")
    st.divider()
    st.caption("Last updated: " + datetime.now().strftime("%H:%M:%S"))

if not st.session_state.get("chatting"):
    st_autorefresh(interval=max(interval, 15) * 1000, key="autorefresh")

if "logs_history" not in st.session_state:
    st.session_state.logs_history = pd.DataFrame(columns=[
        "timestamp", "source_ip", "event_type",
        "login_attempts", "bytes_transferred", "Prediction", "Risk"
    ])
if "attack_explanations" not in st.session_state:
    st.session_state.attack_explanations = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

event_types_normal = ["login_success", "file_download", "api_request", "logout"]

#Function to generate normal log
def generate_normal_log():
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_ip": faker.ipv4(),
        "event_type": random.choice(event_types_normal),
        "login_attempts": random.randint(1, 3),
        "bytes_transferred": random.randint(100, 1500),
    }

#Function to generate attack log incase at some point LLM generation fails
def generate_local_attack_log():
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_ip": faker.ipv4(),
        "event_type": random.choice(attack_types),
        "login_attempts": random.randint(3, 12),
        "bytes_transferred": random.randint(2000, 120000),
    }

#Function to generate synthetic attack log using llm
def generate_llm_attack(max_retries=1):
    if not use_llm:
        return None
    prompt = """Generate EXACTLY 1 realistic cybersecurity attack log.
Output MUST be a JSON array with exactly 1 object. NO extra text.
FORMAT:
[{"timestamp": "YYYY-MM-DD HH:MM:SS", "source_ip": "X.X.X.X", "event_type": "brute_force OR port_scan OR data_exfiltration", "login_attempts": integer, "bytes_transferred": integer}]"""
    for _ in range(max_retries):
        try:
            response = ollama.chat(model="llama3.1", messages=[{"role": "user", "content": prompt}])
            text = response.message.content.strip()
            json_text = text[text.find("["):text.rfind("]") + 1]
            try:
                logs = json.loads(json_text)
            except Exception:
                logs = ast.literal_eval(json_text)
            if logs and isinstance(logs, list) and logs[0]:
                return logs[0]
        except Exception as e:
            print("LLM retry failed:", e)
    return None

#To generate any log(normal or attack) based on probability
def generate_log(prob):
    if random.random() < prob:
        log = generate_llm_attack()
        return log if log else generate_local_attack_log()
    return generate_normal_log()

#Function to make the llm explain any selected attack
def explain_attack(log_dict):
    prompt = f"""SOC analyst. One line each, no intro:
- Attack Type:
- Severity: HIGH/MEDIUM/LOW (reason in 5 words)
- Intent:
- Mitigation:

Log: {log_dict}"""
    try:
        response = ollama.chat(model="llama3.1", messages=[{"role": "user", "content": prompt}])
        return response.message.content
    except Exception as e:
        login = log_dict.get("login_attempts", 0)
        bytes_ = log_dict.get("bytes_transferred", 0)
        event_type = str(log_dict.get("event_type", "unknown")).replace("_", " ")
        risk_hint = "HIGH" if login >= 8 or bytes_ >= 50000 else "MEDIUM" if login >= 4 or bytes_ >= 5000 else "LOW"
        return f"- Attack Type: {event_type}\n- Severity: {risk_hint}\n- Intent: unauthorized access\n- Mitigation: block IP, review logs"

#Generating a log and labelling it
new_log_dict = generate_log(attack_prob)

#Making prediction using the model to classify the generated log
if new_log_dict:
    pred_result = predict(new_log_dict)
    new_log = pd.DataFrame([new_log_dict])
    new_log["Prediction"] = "ATTACK" if pred_result["Prediction"] == "ATTACK" else "SAFE"
    new_log["Risk"] = pred_result.get("Risk", "LOW")
    st.session_state.logs_history = pd.concat(
        [st.session_state.logs_history, new_log], ignore_index=True
    ).tail(50)

#Streamlit settings
st.markdown("## Security Monitoring Dashboard")
st.caption("AI POWERED SECURITY ANALYST SYSTEM")

df = st.session_state.logs_history

#Final count of metrics
if not df.empty:
    total   = len(df)
    attacks = int((df["Prediction"] == "ATTACK").sum())
    safes   = total - attacks
    highs   = int((df["Risk"] == "HIGH").sum())

    st.markdown(f"""
<div class="metric-row">
  <div class="metric-card"><p class="m-label">Total logs</p><p class="m-value">{total}</p></div>
  <div class="metric-card attack"><p class="m-label">Attacks</p><p class="m-value">{attacks}</p></div>
  <div class="metric-card safe"><p class="m-label">Safe</p><p class="m-value">{safes}</p></div>
  <div class="metric-card high"><p class="m-label">High risk</p><p class="m-value">{highs}</p></div>
</div>
""", unsafe_allow_html=True)

st.divider()

    
if not df.empty:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown('<p class="section-label">Attack vs Safe over time</p>', unsafe_allow_html=True)
        df["time"] = pd.to_datetime(df["timestamp"])
        timeline = df.groupby(["time", "Prediction"]).size().reset_index(name="count")
        chart = alt.Chart(timeline).mark_line(point=True).encode(
            x=alt.X("time:T", title="Time"),
            y=alt.Y("count:Q", title="Count"),
            color=alt.Color("Prediction:N", scale=alt.Scale(
                domain=["ATTACK", "SAFE"],
                range=["#E24B4A", "#1D9E75"]
            )),
        ).properties(height=200)
        st.altair_chart(chart, use_container_width=True)

    with chart_col2:
        st.markdown('<p class="section-label">Event type breakdown</p>', unsafe_allow_html=True)
        event_counts = df["event_type"].value_counts().reset_index()
        event_counts.columns = ["event_type", "count"]
        bar = alt.Chart(event_counts).mark_bar().encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("event_type:N", sort="-x", title=""),
            color=alt.value("#6366f1"),
        ).properties(height=200)
        st.altair_chart(bar, use_container_width=True)

    st.divider()

#Setting main layout - Left for the logs table which shows all the logs and right for the explanation
col_logs, col_panel = st.columns([3, 1.2], gap="large")

attack_logs = df[df["Prediction"] == "ATTACK"].reset_index(drop=True) if not df.empty else pd.DataFrame()

#For log table
with col_logs:
    st.markdown('<p class="section-label">Live logs</p>', unsafe_allow_html=True)

    def colour_row(row):
        if row["Prediction"] == "ATTACK":
            return ["background-color: #FCEBEB; color: #501313"] * len(row)
        return [""] * len(row)

    display_cols = ["timestamp", "source_ip", "event_type",
                    "login_attempts", "bytes_transferred", "Prediction", "Risk"]
    shown = df[display_cols] if not df.empty else pd.DataFrame(columns=display_cols)

    st.dataframe(
        shown.style.apply(colour_row, axis=1),
        use_container_width=True,
        height=480,
        hide_index=True,
    )

#LLM Explanation part
with col_panel:
    st.markdown('<p class="section-label">AI Security Analyst</p>', unsafe_allow_html=True)
    selected_row = None
    log_key = None

    if attack_logs.empty:
        st.info("No attacks detected yet.", icon="🛡️")
    else:
        attack_options = [
            f"{row['timestamp']} · {row['event_type']} · {row['source_ip']}"
            for _, row in attack_logs.iterrows()
        ]

        selected_label = st.selectbox(
            "Select attack",
            attack_options,
            index=attack_options.index(st.session_state.get("selected_label", attack_options[0])) if st.session_state.get("selected_label") in attack_options else 0,
            label_visibility="collapsed",
            key="attack_selectbox",
        )
        st.session_state.selected_label = selected_label

        selected_idx = attack_options.index(selected_label)
        selected_row = attack_logs.iloc[selected_idx]
        new_key = f"{selected_row['timestamp']}_{selected_row['source_ip']}_{selected_row['event_type']}"
        st.session_state.selected_attack = selected_row.to_dict()
        st.session_state.last_selected_key = new_key
        log_key = f"{selected_row['timestamp']}_{selected_row['source_ip']}_{selected_row['event_type']}"
        st.caption("Selected alert is used for explanation and chat.")

    #LLM explanation
    if selected_row is not None:
        st.markdown('<div class="divider-label">AI Explanation</div>', unsafe_allow_html=True)

        if log_key not in st.session_state.attack_explanations:
            st.session_state.attack_explanations[log_key] = explain_attack(selected_row.to_dict())
        
        explanation = st.session_state.attack_explanations[log_key]

        st.session_state.attack_explanations[log_key] = explanation
        st.markdown(f'<div class="explanation-box">{explanation}</div>', unsafe_allow_html=True)

#Chatbot section

st.divider()
st.markdown('<p class="section-label">Ask the analyst</p>', unsafe_allow_html=True)

if attack_logs.empty:
    st.caption("An attack must be detected before you can ask questions.")
else:
    for role, msg in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(msg)

    user_qn = st.chat_input("Ask about the selected attack…")

    if user_qn:
        selected_attack_dict = st.session_state.get("selected_attack")

        if not selected_attack_dict:
            st.warning("Please select an attack first.")
            st.stop()

        st.session_state.chat_history.append(("user", user_qn))
        with st.chat_message("user"):
            st.markdown(user_qn)

        prompt = f"""You are a cybersecurity analyst.

Attack log:
{selected_attack_dict}

User question:
{user_qn}

Answer briefly and professionally."""

        st.session_state.chatting = True
        try:
            response = ollama.chat(
                model="llama3.1",
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.message.content
        except Exception as e:
            answer = f"Error: {str(e)}"

        with st.chat_message("assistant"):
            st.markdown(answer)

        st.session_state.chat_history.append(("assistant", answer))
        st.rerun()

with st.expander("Debug — latest log", expanded=False):
    st.json(new_log_dict)