import streamlit as st

# counter = 0
# button = st.button("카운터 증가")
# if button:
#     counter = counter + 1
#     st.write(counter)

state = st.session_state

if "counter" not in st.session_state:
    state.counter = 0
button = st.button("카운터 증가")
if button:
    state.counter = state.counter + 1
st.write(state.counter)
