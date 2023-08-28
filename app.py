import streamlit as st
import data_viewer


tab1, tab2 = st.tabs(["Tab 1", "Data Viewer"])
with tab1:
    st.title("Hello World")

with tab2:
    data_viewer.main()
