import pandas as pd
from slugify import slugify
from collections import defaultdict

def process_excel_data():
    # Read the Excel file
    df = pd.read_excel('data/SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx')
    
    # Clean and process the data
    df['slug'] = df['Store Name'].apply(slugify)
    df['city_slug'] = df['City'].apply(slugify)
    df['state_slug'] = df['State'].apply(slugify)
    
    # Sort by review count descending
    df = df.sort_values('Review Count', ascending=False)
    
    return df

def get_states_data(df):
    states_data = {}
    for state in df['State'].unique():
        state_df = df[df['State'] == state]
        states_data[state] = {
            'name': state,
            'slug': slugify(state),
            'abbr': state_df['State Abbreviation'].iloc[0],
            'store_count': len(state_df),
            'city_count': len(state_df['City'].unique()),
            'cities': get_cities_data(state_df)
        }
    return states_data

def get_cities_data(state_df):
    cities_data = {}
    for city in state_df['City'].unique():
        city_df = state_df[state_df['City'] == city]
        cities_data[city] = {
            'name': city,
            'slug': slugify(city),
            'store_count': len(city_df),
            'stores': get_stores_data(city_df)
        }
    return cities_data

def get_stores_data(city_df):
    stores = []
    for _, row in city_df.iterrows():
        stores.append({
            'name': row['Store Name'],
            'slug': slugify(row['Store Name']),
            'address': row['Address'],
            'phone': row['Phone'],
            'rating': row['Rating'],
            'review_count': row['Review Count'],
            'description': row['New SEO Description V2'],
            'categories': row['Categories'].split(',') if pd.notna(row['Categories']) else [],
            'hours': row['Hours']
        })
    return stores

def get_nearby_cities(df, state, city, limit=10):
    state_df = df[df['State'] == state]
    current_city_lat = state_df[state_df['City'] == city]['Latitude'].iloc[0]
    current_city_lon = state_df[state_df['City'] == city]['Longitude'].iloc[0]
    
    # Calculate distances and get nearest cities
    state_df['distance'] = ((state_df['Latitude'] - current_city_lat) ** 2 + 
                           (state_df['Longitude'] - current_city_lon) ** 2) ** 0.5
    
    nearby_cities = (state_df[state_df['City'] != city]
                    .sort_values('distance')
                    .drop_duplicates('City')
                    .head(limit))
    
    return [{'name': row['City'], 
             'slug': slugify(row['City']),
             'store_count': len(df[df['City'] == row['City']])} 
            for _, row in nearby_cities.iterrows()]