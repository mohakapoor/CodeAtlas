import polars as pl
import numpy as np
import joblib
import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

# Pre-load scalars 
MINMAX = joblib.load(os.getenv('PATH_MINMAX'))
STANDARD = joblib.load(os.getenv('PATH_STANDARD'))
PCA = joblib.load(os.getenv('PATH_PCA'))


# loading data
df = pl.read_parquet("unscaled_test.parquet").with_row_index("original_index")
y_test = df["Attack"]
indices = df["original_index"]
x = df.drop(["Attack", "original_index"])


def len_df():
    return df.shape[0]

def sampler(target_class):

    sample_df = df.filter(pl.col("Attack") == target_class).sample(1)
    
    if sample_df.height == 0:
        raise ValueError(f"No data found for class {target_class}")
    
    idx = sample_df["original_index"][0]
    features = sample_df.drop(["Attack", "original_index"]).to_numpy()
    
    return features, idx


def sample_by_index(idx):
    sample_df = df.filter(pl.col("original_index") == idx)

    if sample_df.height == 0:
        raise ValueError(f"No data found for index {idx}")
    
    target_class = sample_df["Attack"][0]

    features = sample_df.drop(["Attack", "original_index"]).to_numpy()

    return features,target_class

def scale_unsupervised(flow):
    return MINMAX.transform(flow)

def scale_supervised(flow):
    flow = STANDARD.transform(flow)
    flow = PCA.transform(flow)
    return flow

def handle_values(df):
    df = df.fillna(0)
    df = df.replace([np.inf,-np.inf],0)
    return df

def downcast_dtypes(df):
    for col in df.columns:
        col_type = df[col].dtype
        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type).find('float') >= 0:
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
            elif str(col_type).find('int') >= 0:
                if c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
    return df

def preprocess_new_data(df, is_labeled=True):
    # Column Name Cleanup
    df.columns = df.columns.str.strip()
    
    # Value Handling (NaN and Inf)
    df = handle_values(df)
    
    # Drop Redundant Columns
    if 'Fwd Header Length.1' in df.columns:
        df = df.drop('Fwd Header Length.1', axis=1)
        
    # Constant columns identified in preprocessing.ipynb (nunique == 1)
    constant_cols = [
        'Bwd PSH Flags', 'Bwd URG Flags', 'Fwd Avg Bytes/Bulk',
        'Fwd Avg Packets/Bulk', 'Fwd Avg Bulk Rate', 'Bwd Avg Bytes/Bulk',
        'Bwd Avg Packets/Bulk', 'Bwd Avg Bulk Rate'
    ]
    cols_to_drop = [c for c in constant_cols if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    
    # Data Type Downcasting
    df = downcast_dtypes(df)
    
    return df