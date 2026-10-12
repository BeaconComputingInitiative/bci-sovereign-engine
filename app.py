# Beacon Computing Initiative | Erudite | Developer Seal: Chance Joaquin Boone (CJB)
# Developers seal: Chance Joaquin Boone

import os
import subprocess
import streamlit as st
import torch
import torch.nn as nn

st.set_page_config(
    page_title="Erudite",
    page_icon="⚡",
    layout="wide"
)

# --- Model Definition for Chat Inference ---
class SovereignTransformer(nn.Module):
    def __init__(self, vocab_size: int = 2048, d_model: int = 512, nhead: int = 8, num_layers: int = 6, max_len: int = 128):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_embedding = nn.Parameter(torch.zeros(1, max_len, d_model))
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=d_model * 4, 
            dropout=0.1,
            activation='gelu',
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.norm = nn.LayerNorm(d_model)
        self.fc_out = nn.Linear(d_model, vocab_size)

    def forward(self, x):
        seq_len = x.size(1)
        h = self.embedding(x) + self.pos_embedding[:, :seq_len, :]
        mask = nn.Transformer.generate_square_subsequent_mask(seq_len).to(x.device)
        h = self.transformer_encoder(h, mask=mask, is_causal=True)
        h = self.norm(h)
        return self.fc_out(h)

@st.cache_resource
def load_sovereign_model():
    ckpt_path = "checkpoints/bci_sovereign_model.pt"
    model = SovereignTransformer(vocab_size=2048, d_model=512, nhead=8, num_layers=6, max_len=128)
    device = torch.device("cpu")
    if os.path.exists(ckpt_path):
        try:
            model.load_state_dict(torch.load(ckpt_path, map_location=device))
            model.eval()
            return model, True
        except Exception:
            return model, False
    return model, False

# Sidebar Navigation
st.sidebar.title("Erudite")
st.sidebar.caption("Beacon Computing Initiative")
st.sidebar.caption("Developer Seal: Chance Joaquin Boone (CJB)")
page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard & Telemetry", "Admin & Model Controls", "Erudite Terminal", "Erudite Chat"]
)

def render_dashboard():
    st.title("Erudite · Operations Dashboard")
    st.markdown("Real-time telemetry and operational overview for local node inference and training.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Architecture", "Causal Transformer", "6 Layers, 512d")
    with col2:
        st.metric("Device Status", "CPU Active", "PyTorch 2.x")
    with col3:
        checkpoint_exists = os.path.exists("checkpoints/bci_sovereign_model.pt")
        st.metric("Model Checkpoint", "Secured" if checkpoint_exists else "Not Found", "checkpoints/")

    st.divider()
    st.subheader("Corpus Status")
    datasets = [
        "dataset/dataset_combined_30k.jsonl",
        "dataset/dataset_code.jsonl",
        "dataset/dataset_prose.jsonl",
        "dataset/bci_knowledge.md"
    ]
    
    for ds in datasets:
        if os.path.exists(ds):
            size_kb = os.path.getsize(ds) / 1024
            st.text(f"✔ {ds} ({size_kb:.1f} KB)")
        else:
            st.text(f"✘ {ds} (Missing)")

def render_admin():
    st.title("Erudite · Model Controls")
    st.markdown("Execute maintenance tasks, trigger live training sequences, and manage checkpoint files.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Training Pipeline Controls")
        if st.button("🚀 Launch Live Training Run"):
            with st.status("Initializing BCI Sovereign Training...", expanded=True) as status:
                st.write("Spawning training subprocess...")
                
                try:
                    process = subprocess.Popen(
                        ["python3", "train_pipeline.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        line_clean = line.strip()
                        if line_clean:
                            status.update(label=f"Training: {line_clean[-60:]}", state="running")
                            st.text(line_clean)
                    
                    process.stdout.close()
                    return_code = process.wait()
                    
                    if return_code == 0:
                        status.update(label="Training sequence completed successfully!", state="complete", expanded=False)
                        st.success("Sovereign model weights updated and secured in checkpoints/")
                    else:
                        status.update(label="Training sequence encountered an error.", state="error", expanded=True)
                        st.error("Check logs above for details.")
                except Exception as e:
                    status.update(label="Failed to spawn training process.", state="error", expanded=True)
                    st.error(f"Execution Error: {str(e)}")
                    
    with col2:
        st.subheader("Checkpoint Management")
        ckpt_path = "checkpoints/bci_sovereign_model.pt"
        if os.path.exists(ckpt_path):
            file_size = os.path.getsize(ckpt_path) / (1024 * 1024)
            st.info(f"Active checkpoint found: `{ckpt_path}` ({file_size:.2f} MB)")
            if st.button("🗑️ Purge Checkpoint Weights"):
                os.remove(ckpt_path)
                st.warning("Checkpoint weights purged.")
                st.rerun()
        else:
            st.warning("No active checkpoint file found in `checkpoints/`.")

def render_terminal():
    st.title("Erudite · Terminal")
    st.markdown("Execute system commands directly within the local BCI environment node.")
    
    if "terminal_history" not in st.session_state:
        st.session_state.terminal_history = []

    with st.form(key="terminal_form", clear_on_submit=True):
        user_cmd = st.text_input("Node Shell Input:", placeholder="e.g., ls -la dataset/, sensors, python3 train_pipeline.py")
        submit_button = st.form_submit_button(label="Execute Command")
        
        if submit_button and user_cmd:
            try:
                process = subprocess.run(user_cmd, shell=True, capture_output=True, text=True, timeout=15)
                output = process.stdout if process.returncode == 0 else process.stderr
                if not output.strip():
                    output = "[Command executed successfully with no output]"
            except Exception as e:
                output = f"Execution Error: {str(e)}"
                
            st.session_state.terminal_history.append({"cmd": user_cmd, "out": output})

    if st.session_state.terminal_history:
        if st.button("Clear History"):
            st.session_state.terminal_history = []
            st.rerun()
            
        st.divider()
        for item in reversed(st.session_state.terminal_history):
            st.markdown(f"**node@bci:~$ `{item['cmd']}`**")
            st.code(item['out'])

def render_chat():
    st.title("Erudite · Chat")
    st.markdown("Interact directly with the local BCI neural engine.")
    
    model, is_loaded = load_sovereign_model()
    if is_loaded:
        st.success("🟢 Sovereign model weights loaded successfully for inference.")
    else:
        st.warning("🟡 No checkpoint found or loaded; using fallback generator mode until training completes.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Beacon Computing Initiative chat node online. How can I assist your workflow?"}
        ]

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Type your message here..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Generating response from local node..."):
                if is_loaded:
                    input_ids = [ord(c) % 2048 for c in prompt[:64]]
                    generated = list(input_ids)
                    model.eval()
                    with torch.no_grad():
                        for _ in range(30):
                            if len(generated) >= 128:
                                break
                            curr_tensor = torch.tensor([generated[-64:]], dtype=torch.long)
                            outputs = model(curr_tensor)
                            next_token_logits = outputs[0, -1, :]
                            next_token = torch.argmax(next_token_logits).item()
                            generated.append(next_token)
                    
                    response_text = "".join([chr(t) if 32 <= t <= 126 else "." for t in generated[len(input_ids):]])
                    if not response_text.strip():
                        response_text = f"Processed prompt on local node [Length: {len(prompt)} chars]. Checkpoint active."
                else:
                    response_text = f"Acknowledged: '{prompt}'. Please complete a training run in the Admin panel to activate neural generation weights."
                
                st.markdown(response_text)
                st.session_state.chat_messages.append({"role": "assistant", "content": response_text})

if page == "Dashboard & Telemetry":
    render_dashboard()
elif page == "Admin & Model Controls":
    render_admin()
elif page == "Erudite Terminal":
    render_terminal()
elif page == "Erudite Chat":
    render_chat()

