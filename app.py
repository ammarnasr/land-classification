import streamlit as st
import data_viewer
import data_downloader
import data_reader


tab1, tab2, tab3, tab4 = st.tabs(["Tab 1", "Label Viewer", "Data Downloader", "Data Reader"])
with tab1:
    st.title("Hello World")

with tab2:
    data_viewer.main()

with tab3:
    data_downloader.main()

with tab4:
    data_reader.main()
