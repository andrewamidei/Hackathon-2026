import streamlit as st
import time
from datetime import datetime

st.title("Game Page")

st.markdown(f"lobby code {st.session_state.login_code}")

# # -----------------------------------
# # GLOBAL SERVER STATE (shared by users)
# # -----------------------------------
# if "MESSAGES" not in globals():
#     MESSAGES = []   # shared across all sessions

# # -----------------------------------
# # Page config
# # -----------------------------------
# st.set_page_config(page_title="Online Group Chat", layout="centered")
# st.title("💬 Online Group Chat (Online Users Only)")

# # -----------------------------------
# # Username handling (per session)
# # -----------------------------------
# if "username" not in st.session_state:
#     st.session_state.username = None

# if st.session_state.username is None:
#     username = st.text_input("Enter a username")

#     if st.button("Join") and username.strip():
#         st.session_state.username = username.strip()
#         st.rerun()

#     st.stop()

# st.caption(f"Logged in as **{st.session_state.username}**")
# st.divider()

# # -----------------------------------
# # CHAT DISPLAY
# # -----------------------------------
# chat_box = st.container()

# with chat_box:
#     for msg in MESSAGES:
#         user, text, ts = msg
#         if user == st.session_state.username:
#             st.markdown(
#                 f"<div style='text-align:right'><b>{user}</b> ({ts})<br>{text}</div>",
#                 unsafe_allow_html=True
#             )
#         else:
#             st.markdown(
#                 f"<div><b>{user}</b> ({ts})<br>{text}</div>",
#                 unsafe_allow_html=True
#             )

# st.divider()

# # -----------------------------------
# # MESSAGE INPUT
# # -----------------------------------
# message = st.text_input("Type a message", key="message_input")

# if st.button("Send") and message.strip():
#     MESSAGES.append(
#         (
#             st.session_state.username,
#             message.strip(),
#             datetime.now().strftime("%H:%M:%S"),
#         )
#     )
#     st.session_state.message_input = ""
#     st.rerun()

# # -----------------------------------
# # AUTO REFRESH (simple polling)
# # -----------------------------------
# time.sleep(1)
# st.rerun()