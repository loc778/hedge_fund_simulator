# data/export_features.py
# Exports features_master to CSV for Google Colab training
# Run this whenever you want to retrain models with fresh data

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from data.db import get_engine
from config import TABLES

engine = get_engine()

print("📥 Loading features from MySQL...")
df = pd.read_sql(f"SELECT * FROM {TABLES['features']}", con=engine)

print(f"✅ Loaded {len(df):,} rows × {len(df.columns)} columns")

# Save to project folder
output_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "features_master.csv"
)

df.to_csv(output_path, index=False)
print(f"✅ Saved to {output_path}")
print(f"   File size: {os.path.getsize(output_path) / 1024 / 1024:.1f} MB")
print(f"\n📤 Next step: Upload features_master.csv to Google Drive")