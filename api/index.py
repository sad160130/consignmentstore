from flask import Flask, render_template, request, redirect, url_for, Response, make_response, send_from_directory
import pandas as pd
from slugify import slugify
from datetime import datetime
from collections import defaultdict
import logging
import sys
import os
import json

# Initialize Flask app with explicit template and static paths
app = Flask(__name__,
           template_folder='../templates',  # Updated path for Vercel
           static_folder='../static')       # Updated path for Vercel

# Configure logging for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Define regions
REGIONS = {
    'Northeast': ['Maine', 'New Hampshire', 'Vermont', 'Massachusetts', 'Rhode Island', 
                 'Connecticut', 'New York', 'Pennsylvania', 'New Jersey'],
    'Midwest': ['Ohio', 'Indiana', 'Michigan', 'Illinois', 'Wisconsin', 'Minnesota', 
               'Iowa', 'Missouri', 'North Dakota', 'South Dakota', 'Nebraska', 'Kansas'],
    'South': ['Delaware', 'Maryland', 'Virginia', 'West Virginia', 'North Carolina',
             'South Carolina', 'Georgia', 'Florida', 'Kentucky', 'Tennessee', 'Alabama',
             'Mississippi', 'Arkansas', 'Louisiana', 'Oklahoma', 'Texas'],
    'West': ['Montana', 'Idaho', 'Wyoming', 'Colorado', 'New Mexico', 'Arizona', 'Utah',
            'Nevada', 'Washington', 'Oregon', 'California', 'Alaska', 'Hawaii']
}

def safe_str(value):
    """Safely convert any value to string"""
    if pd.isna(value):
        return ''
    return str(value)

def safe_slugify(value):
    """Safely create a slug from any value"""
    return slugify(safe_str(value))

def load_data():
    """Load and process the data"""
    try:
        # Updated path for Vercel
        base_path = os.path.dirname(os.path.dirname(__file__))
        
        # First try to load from JSON file
        json_path = os.path.join(base_path, 'data', 'SEO_Optimized_Consignment_Stores_Sample_Dataset.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data)
        else:
            # Try loading from Excel if JSON not found
            excel_path = os.path.join(base_path, 'data', 'SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx')
            if not os.path.exists(excel_path):
                logger.error(f"Data file not found at: {excel_path}")
                return None
            df = pd.read_excel(excel_path)

        if df.empty:
            logger.error("Data file is empty")
            return None

        # Clean and convert data types
        df = df.fillna('')
        for col in df.columns:
            df[col] = df[col].apply(safe_str)

        # Convert numeric columns
        df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0.0)
        df['Number of Reviews'] = pd.to_numeric(df['Number of Reviews'], errors='coerce').fillna(0)

        # Generate slugs
        df['slug'] = df['Business Name'].apply(safe_slugify)
        df['city_slug'] = df['City'].apply(safe_slugify)
        df['state_slug'] = df['State'].apply(safe_slugify)

        df = df.sort_values('Number of Reviews', ascending=False)
        logger.info(f"Successfully loaded {len(df)} records")
        return df

    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return None

# ... [Previous helper functions remain the same] ...
# Keep all the existing functions: format_description, process_data, get_nearby_cities

# Load data at startup
logger.info("=== Starting Consignment Directory Server ===")
logger.info("Initializing data...")
df = load_data()
states_data = process_data(df) if df is not None else {}

# ... [Previous routes and context processors remain the same] ...
# Keep all the existing routes and the context processor

# For Vercel deployment
app.debug = False

# Remove the if __name__ == '__main__': block
# Instead, add this line at the end:
app = app