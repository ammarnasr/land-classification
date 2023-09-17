import streamlit as st
import data_viewer
import data_downloader
import data_reader
import data_processor
import model_trainer
import data_inference_collector
import data_inference_downloader

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Tab 1", 
    "Label Viewer", 
    "Data Downloader",
    "Data Reader",
    "Data Processor",
    "Model Trainer",
    "Data Inference Collector",
    "Data Inference Downloader"
    ])
with tab1:
    st.title("Hello World")

with tab2:
    st.title("Label Viewer")
    # data_viewer.main()

with tab3:
    st.title("Data Downloader")
    # data_downloader.main()

with tab4:
    st.title("Data Reader")
    data_reader.main()

with tab5:
    st.title("Data Processor")
    # data_processor.main()
    
with tab6:
    st.title("Model Trainer")
    # model_trainer.main()

with tab7:
    st.title("Data Inference Collector")
    # data_inference_collector.main()

with tab8:
    st.title("Data Inference Downloader")
    # data_inference_downloader.main()
