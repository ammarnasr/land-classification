from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from sklearn.utils import resample
import joblib
import os
import pickle
import geopandas as gpd
import streamlit as st


def read_all_processed_data(file_path='./data/joblibs/processed_data.joblib'):
    processed_data_gdf = joblib.load(file_path)
    processed_data_gdf = processed_data_gdf[processed_data_gdf['Labels'] != -1]
    return processed_data_gdf


def plot_labels_distribution(processed_data_gdf):
    labels_dict = {0: 'Unccultivated', 1: 'Cultivated', 2: 'Other'}
    fig, ax = plt.subplots(figsize=(10, 3))
    processed_data_gdf['Labels'].value_counts().plot(ax=ax, kind='bar')
    ax.set_xticklabels([labels_dict[int(x.get_text())] for x in ax.get_xticklabels()])
    ax.set_xlabel('Labels')
    ax.set_ylabel('Count')
    ax.set_title('Labels Distribution')
    st.pyplot(fig)
    return fig

def balance_data_downsample(processed_data_gdf):
    values, counts = np.unique(processed_data_gdf['Labels'], return_counts=True)
    sorted_indices = np.argsort(counts)
    sorted_counts = counts[sorted_indices]
    sorted_values = values[sorted_indices]
    minority_class = sorted_values[0]
    majority_classes = sorted_values[1:]
    minority_class_count = sorted_counts[0]
    # Downsample majority classes
    processed_data_majority_downsampled = []
    for majority_class in majority_classes:
        processed_data_majority = processed_data_gdf[processed_data_gdf.Labels==majority_class]
        processed_data_majority_downsampled.append(resample(processed_data_majority,
                                        replace=False,    # sample without replacement
                                        n_samples=minority_class_count,     # to match minority class
                                        random_state=123)) # reproducible results
    processed_data_majority_downsampled = pd.concat(processed_data_majority_downsampled)
    processed_data_minority = processed_data_gdf[processed_data_gdf.Labels==minority_class]
    processed_data_downsampled = pd.concat([processed_data_majority_downsampled, processed_data_minority])
    return processed_data_downsampled


def train_and_predict(df, use_october=False, n_estimators=50, max_depth=10, test_size=0.25):
    if not use_october:
        columns = df.columns
        columns_october = [col for col in columns if '-10-' in col]
        df = df.drop(columns_october, axis=1)
    y = df['Labels']
    X = df.drop(['Labels', 'geometry', 'latitude', 'longitude', 'location'], axis=1)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size)
    clf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=0, n_jobs=-1, verbose=2)
    
    with st.spinner('Training model...'):
        clf.fit(X_train, y_train)

    with st.spinner('Evaluating model...'):
        y_pred = clf.predict(X_test)
        st.write('Accuracy score: ', accuracy_score(y_test, y_pred))
        class_report = classification_report(y_test, y_pred, output_dict=True)
        class_report_df = pd.DataFrame(class_report)
        class_report_df = class_report_df.rename(columns={'0': 'Unccultivated', '1': 'Cultivated', '2': 'Other'})
        st.write(class_report_df)
        conf_mat = confusion_matrix(y_test, y_pred)
        fig, ax = plt.subplots(figsize=(10, 3))
        sns.heatmap(conf_mat, annot=True, fmt='d', xticklabels=['Unccultivated', 'Cultivated', 'Other'], yticklabels=['Unccultivated', 'Cultivated', 'Other'])
        ax.set_xlabel('Predicted')
        ax.set_ylabel('Actual')
        ax.set_title('Confusion Matrix')
        st.pyplot(fig)

    return clf

#Feature importance
def feature_importance_plot(clf, df, use_october=False):
    if not use_october:
        columns = df.columns
        columns_october = [col for col in columns if '-10-' in col]
        df = df.drop(columns_october, axis=1)
    X = df.drop(['Labels', 'geometry', 'latitude', 'longitude', 'location'], axis=1)
    feature_importance = clf.feature_importances_
    feature_importance = 100.0 * (feature_importance / feature_importance.max())
    sorted_idx = np.argsort(feature_importance)
    sorted_idx = sorted_idx[-10:]
    pos = np.arange(sorted_idx.shape[0]) + .5
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.barh(pos, feature_importance[sorted_idx], align='center')
    ax.set_yticks(pos)
    ax.set_yticklabels(X.columns[sorted_idx])
    ax.set_xlabel('Relative Importance')
    ax.set_title('Variable Importance')
    st.pyplot(fig)
    return fig

def read_and_dwonsample_data(file_path='./data/joblibs/processed_data.joblib', remove_label = -1):
    downsampled_data_path = os.path.join('./data/joblibs', f'processed_data_downsampled_{remove_label}.joblib')
    if os.path.exists(downsampled_data_path):
        processed_data_downsampled = joblib.load(downsampled_data_path)
        return processed_data_downsampled
    processed_data_gdf = joblib.load(file_path)
    processed_data_gdf = processed_data_gdf[processed_data_gdf['Labels'] != -1]
    processed_data_downsampled = balance_data_downsample(processed_data_gdf)

    if remove_label != -1:
        processed_data_downsampled = processed_data_downsampled[processed_data_downsampled['Labels'] != remove_label]
        processed_data_downsampled = processed_data_downsampled.reset_index(drop=True)

    joblib.dump(processed_data_downsampled, downsampled_data_path)
    return processed_data_downsampled

def normalize_data(df):
    '''
    normalize columns with data type float by mean and std
    '''
    df = df.copy()
    float_columns = df.select_dtypes(include=['float']).columns
    for col in float_columns:
        df[col] = (df[col] - df[col].mean()) / df[col].std()
    return df

def main():
    processed_data_downsampled = read_and_dwonsample_data()
    processed_data_downsampled = normalize_data(processed_data_downsampled)

    st.write('Number of data points ', len(processed_data_downsampled))
    st.write(processed_data_downsampled.head())

    use_october = st.checkbox('Use October data')
    n_estimators = st.slider('Number of estimators', 10, 500, 200)
    max_depth = st.slider('Max depth', 5, 100, 20)
    test_size = st.slider('Test size', 0.1, 0.9, 0.60)
    model_name = st.text_input('Model name', 'RandomForestClassifier')
    start_training = st.button('Start training')

    if start_training:
        clf = train_and_predict(processed_data_downsampled, use_october=use_october, n_estimators=n_estimators, max_depth=max_depth, test_size=test_size)
        model_name = f'{model_name}_n_estimators_{n_estimators}_max_depth_{max_depth}_test_size_{test_size}_use_october_{use_october}_normalized'
        model_path = os.path.join('./data/joblibs', model_name + '.joblib')
        joblib.dump(clf, model_path)
        st.write('Model saved to: ', model_path)
        feature_importance_plot(clf, processed_data_downsampled, use_october=use_october)
    
