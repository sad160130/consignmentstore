from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_caching import Cache
from datetime import datetime
import pandas as pd
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
import os
from slugify import slugify
import json

# Initialize Flask app with explicit template and static paths
app = Flask(__name__, 
    template_folder=os.path.abspath('templates'),
    static_folder=os.path.abspath('static')
)
app.secret_key = 'your-secret-key-here'

# Configure caching
cache = Cache(config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 3600
})
cache.init_app(app)

# Create required directories with absolute paths
base_dir = os.path.abspath(os.path.dirname(__file__))
required_dirs = [
    os.path.join(base_dir, 'logs'),
    os.path.join(base_dir, 'data'),
    os.path.join(base_dir, 'static', 'css'),
    os.path.join(base_dir, 'static', 'images')
]

for directory in required_dirs:
    os.makedirs(directory, exist_ok=True)
    print(f"Verified directory: {directory}")

# Configure logging with absolute path
log_file = os.path.join(base_dir, 'logs', 'app.log')
handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Define US regions
regions = {
    'Northeast': [
        'Connecticut', 'Maine', 'Massachusetts', 'New Hampshire', 'Rhode Island', 
        'Vermont', 'New Jersey', 'New York', 'Pennsylvania'
    ],
    'Midwest': [
        'Illinois', 'Indiana', 'Michigan', 'Ohio', 'Wisconsin', 'Iowa', 'Kansas',
        'Minnesota', 'Missouri', 'Nebraska', 'North Dakota', 'South Dakota'
    ],
    'South': [
        'Delaware', 'Florida', 'Georgia', 'Maryland', 'North Carolina', 
        'South Carolina', 'Virginia', 'West Virginia', 'Alabama', 'Kentucky',
        'Mississippi', 'Tennessee', 'Arkansas', 'Louisiana', 'Oklahoma', 'Texas'
    ],
    'West': [
        'Arizona', 'Colorado', 'Idaho', 'Montana', 'Nevada', 'New Mexico', 'Utah',
        'Wyoming', 'Alaska', 'California', 'Hawaii', 'Oregon', 'Washington'
    ]
}

def safe_str(value):
    """Safely convert value to string, handling None values."""
    return str(value) if value is not None else ''

def safe_slugify(value):
    """Create a safe slug from the given value."""
    return slugify(safe_str(value))

def get_state_counts(df):
    """Calculate the number of stores per state"""
    if df is None or df.empty:
        return {}
    return df.groupby('state').size().to_dict()

def validate_photo_url(url):
    """Validate and clean photo URLs."""
    if pd.isna(url) or not url:
        return ''
    
    url = str(url).strip()
    url = url.replace(' ', '%20')
    
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url

def format_description(description):
    """Format store description into paragraphs."""
    if pd.isna(description) or not description:
        return ''
    
    description = str(description).strip()
    paragraphs = [p.strip() for p in description.split('\n\n')]
    return '\n\n'.join(p for p in paragraphs if p)

def format_meta_description(city_name, state_name, store_count):
    """Format meta description for city pages."""
    return (f"Discover {store_count} consignment stores in {city_name}, {state_name}. "
            "Find local thrift stores, consignment shops, and second-hand boutiques.")

@cache.cached(timeout=3600, key_prefix='load_data')
def load_data():
    """Load store data from Excel file."""
    try:
        file_path = os.path.join(base_dir, 'data', 'SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx')
        
        if not os.path.exists(file_path):
            app.logger.error(f"Data file not found: {file_path}")
            return pd.DataFrame()
            
        df = pd.read_excel(file_path)
        
        # Verify required columns
        required_columns = [
            'Business Name', 'Address', 'City', 'State', 
            'Number of Reviews', 'New SEO Description V2', 
            'Site', 'Phone', 'Photo'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            app.logger.error(f"Missing required columns: {missing_columns}")
            return pd.DataFrame()
        
        # Rename columns for consistency
        df = df.rename(columns={
            'Business Name': 'name',
            'Address': 'address',
            'City': 'city',
            'State': 'state',
            'Number of Reviews': 'review_count',
            'New SEO Description V2': 'description',
            'Site': 'website',
            'Phone': 'phone',
            'Photo': 'photo'
        })
        
        # Convert review count to numeric, replacing NaN with 0
        df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce').fillna(0).astype(int)
        
        # Clean string columns
        string_columns = ['name', 'address', 'city', 'state', 'website', 'phone']
        for col in string_columns:
            df[col] = df[col].fillna('').astype(str).str.strip()
        
        # Process descriptions and photos
        df['description'] = df['description'].apply(format_description)
        df['photo'] = df['photo'].apply(validate_photo_url)
        
        # Add hours column if it doesn't exist
        if 'hours' not in df.columns:
            df['hours'] = 'Hours not available'
        
        app.logger.info(f"Loaded {len(df)} records from dataset")
        app.logger.info(f"Found {df['photo'].notna().sum()} stores with photos")
        return df
        
    except Exception as e:
        app.logger.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def process_data(df):
    """Process DataFrame into structured format."""
    try:
        if df.empty:
            app.logger.error("Empty DataFrame received for processing")
            return {}
            
        processed_data = {}
        
        # Group by state and city
        state_groups = df.groupby('state')
        
        for state_name, state_group in state_groups:
            if not state_name or pd.isna(state_name):
                continue
                
            state_slug = safe_slugify(state_name)
            city_groups = state_group.groupby('city')
            
            cities = []
            total_state_reviews = 0
            
            for city_name, city_group in city_groups:
                if not city_name or pd.isna(city_name):
                    continue
                    
                # Sort stores by review count
                stores = city_group.sort_values('review_count', ascending=False)
                
                city_data = {
                    'name': city_name,
                    'slug': safe_slugify(city_name),
                    'store_count': len(stores),
                    'total_reviews': int(stores['review_count'].sum()),
                    'stores': stores.to_dict('records')
                }
                
                cities.append(city_data)
                total_state_reviews += city_data['total_reviews']
            
            if cities:
                # Sort cities by store count and total reviews
                cities.sort(key=lambda x: (x['store_count'], x['total_reviews']), reverse=True)
                
                processed_data[state_name] = {
                    'name': state_name,
                    'slug': state_slug,
                    'store_count': sum(city['store_count'] for city in cities),
                    'city_count': len(cities),
                    'total_reviews': total_state_reviews,
                    'cities': cities
                }
        
        app.logger.info(f"Processed {len(processed_data)} states")
        return processed_data
        
    except Exception as e:
        app.logger.error(f"Error processing data: {str(e)}")
        return {}

# Load and process data at startup
df = load_data()
processed_data = process_data(df)

@app.context_processor
def utility_processor():
    """Add utility functions and global variables to template context."""
    state_counts = {
        state: data['store_count'] 
        for state, data in processed_data.items()
    }
    
    return {
        'total_stores': sum(state['store_count'] for state in processed_data.values()),
        'total_cities': sum(state['city_count'] for state in processed_data.values()),
        'total_states': len(processed_data),
        'regions': regions,
        'processed_data': processed_data,
        'current_date': datetime.now(),
        'safe_slugify': safe_slugify,
        'state_counts': state_counts,
        'popular_states': sorted(
            processed_data.keys(),
            key=lambda x: processed_data[x]['store_count'],
            reverse=True
        )[:5]
    }

# Custom template filters
@app.template_filter('safe_slugify')
def safe_slugify_filter(text):
    """Convert text to URL-safe slug."""
    return safe_slugify(text)

@app.template_filter('tojson')
def tojson_filter(obj):
    """Convert object to JSON string."""
    return json.dumps(obj)

@app.template_filter('avg')
def avg_filter(values):
    """Calculate average of values."""
    try:
        return sum(values) / len(values)
    except (TypeError, ZeroDivisionError):
        return 0

# Routes
@app.route('/')
def home():
    """Home page route."""
    try:
        # Get the 6 most popular cities based on store count
        popular_cities = []
        for state_data in processed_data.values():
            for city in state_data['cities']:
                city_info = {
                    'name': city['name'],
                    'state': state_data['name'],
                    'state_slug': state_data['slug'],
                    'slug': safe_slugify(city['name']),
                    'store_count': city['store_count'],
                    'total_reviews': city['total_reviews']
                }
                popular_cities.append(city_info)
        
        popular_cities.sort(key=lambda x: (x['store_count'], x['total_reviews']), reverse=True)
        popular_cities = popular_cities[:6]
        
        return render_template(
            'home.html',
            popular_cities=popular_cities,
            title="Find Local Consignment Stores | Thrift Store Directory",
            meta_description="Discover local consignment stores, thrift shops, and second-hand boutiques. "
                           f"Browse our directory of {sum(state['store_count'] for state in processed_data.values())} "
                           f"stores across {len(processed_data)} states."
        )
    except Exception as e:
        app.logger.error(f"Error in home route: {str(e)}")
        return render_template('error.html'), 500

@app.route('/state/<state_name>')
def state(state_name):
    """State page route."""
    try:
        # Find state data
        state_data = next(
            (data for state, data in processed_data.items() 
             if safe_slugify(state) == state_name),
            None
        )
        
        if not state_data:
            app.logger.warning(f"State not found: {state_name}")
            return render_template('404.html'), 404
        
        return render_template(
            'state.html',
            state=state_data,
            cities=state_data['cities'],
            state_name=state_name,
            title=f"Consignment Stores in {state_data['name']} | Thrift Store Directory",
            meta_description=f"Find consignment stores in {state_data['name']}. Browse our directory "
                           f"of {state_data['store_count']} stores across {state_data['city_count']} cities."
        )
    except Exception as e:
        app.logger.error(f"Error in state route: {str(e)}")
        return render_template('error.html'), 500

@app.route('/state/<state_name>/<city_name>')
def city(state_name, city_name):
    """City page route."""
    try:
        # Find state data
        state_data = next(
            (data for state, data in processed_data.items() 
             if safe_slugify(state) == state_name),
            None
        )
        
        if not state_data:
            app.logger.warning(f"State not found: {state_name}")
            return render_template('404.html'), 404
            
        # Find city data
        city_data = next(
            (city for city in state_data['cities'] 
             if safe_slugify(city['name']) == city_name),
            None
        )
        
        if not city_data:
            app.logger.warning(f"City not found: {city_name} in state {state_name}")
            return render_template('404.html'), 404
        
        # Get nearby cities (up to 6)
        nearby_cities = [
            city for city in state_data['cities']
            if safe_slugify(city['name']) != city_name
        ][:6]
        
        return render_template(
            'city.html',
            state=state_data,
            city=city_data,
            stores=city_data['stores'],
            nearby_cities=nearby_cities,
            title=f"Consignment Stores in {city_data['name']}, {state_data['name']}",
            meta_description=format_meta_description(
                city_data['name'],
                state_data['name'],
                city_data['store_count']
            )
        )
    except Exception as e:
        app.logger.error(f"Error in city route: {str(e)}")
        return render_template('error.html'), 500

@app.route('/about')
def about():
    """About page route."""
    try:
        return render_template(
            'about.html',
            title="About Our Consignment Store Directory",
            meta_description="Learn about our mission to connect shoppers with local "
                           "consignment stores, thrift shops, and second-hand boutiques."
        )
    except Exception as e:
        app.logger.error(f"Error in about route: {str(e)}")
        return render_template('error.html'), 500

@app.route('/search')
def search():
    """Search route."""
    try:
        query = request.args.get('q', '').strip().lower()
        
        if not query:
            popular_states = sorted(
                [{'name': k, 'slug': v['slug'], 'store_count': v['store_count']}
                 for k, v in processed_data.items()],
                key=lambda x: x['store_count'],
                reverse=True
            )[:12]
            
            return render_template(
                'search.html',
                query='',
                popular_states=popular_states,
                states=[],
                cities=[],
                stores=[],
                title="Search Consignment Stores | Thrift Store Directory",
                meta_description="Search for local consignment stores, thrift shops, "
                               "and second-hand boutiques in your area."
            )
        
        # Search states, cities, and stores
        states = []
        cities = []
        stores = []
        
        for state_name, state_data in processed_data.items():
            # State matches
            if query in state_name.lower():
                states.append({
                    'name': state_name,
                    'slug': state_data['slug'],
                    'store_count': state_data['store_count'],
                    'city_count': state_data['city_count']
                })
            
            # City matches
            for city in state_data['cities']:
                if query in city['name'].lower():
                    cities.append({
                        'name': city['name'],
                        'state_name': state_name,
                        'state_slug': state_data['slug'],
                        'slug': safe_slugify(city['name']),
                        'store_count': city['store_count'],
                        'total_reviews': city['total_reviews']
                    })
                
                # Store matches
                for store in city['stores']:
                    if query in store['name'].lower():
                        store_info = store.copy()
                        store_info.update({
                            'city': city['name'],
                            'state': state_name,
                            'city_slug': safe_slugify(city['name']),
                            'state_slug': state_data['slug']
                        })
                        stores.append(store_info)
        
        return render_template(
            'search.html',
            query=query,
            states=states,
            cities=cities,
            stores=stores,
            title=f"Search Results for '{query}' | Consignment Store Directory",
            meta_description=f"Search results for '{query}'. Find local consignment stores, "
                           "thrift shops, and second-hand boutiques in your area."
        )
    except Exception as e:
        app.logger.error(f"Error in search route: {str(e)}")
        return render_template('error.html'), 500

@app.route('/sitemap')
def sitemap():
    """HTML sitemap route."""
    try:
        return render_template(
            'sitemap.html',
            title="Sitemap | Consignment Store Directory",
            meta_description="Browse our complete directory of consignment stores, "
                           "thrift shops, and second-hand boutiques."
        )
    except Exception as e:
        app.logger.error(f"Error in sitemap route: {str(e)}")
        return render_template('error.html'), 500

@app.route('/sitemap.xml')
def sitemap_xml():
    """XML sitemap route."""
    try:
        response = make_response(
            render_template(
                'sitemap.xml',
                current_date=datetime.now(),
                processed_data=processed_data
            )
        )
        response.headers['Content-Type'] = 'application/xml'
        response.headers['Cache-Control'] = 'public, max-age=86400'
        return response
    except Exception as e:
        app.logger.error(f"Error generating sitemap.xml: {str(e)}")
        return make_response("Error generating sitemap", 500)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """404 error handler."""
    app.logger.warning(f"404 error: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """500 error handler."""
    app.logger.error(f"500 error: {str(e)}")
    return render_template('error.html'), 500

if __name__ == '__main__':
    try:
        print("\nStarting Flask Application...")
        print("============================")
        
        # Verify directories
        for directory in required_dirs:
            if os.path.exists(directory):
                print(f"✓ Directory exists: {directory}")
            else:
                print(f"✗ Missing directory: {directory}")
        
        # Check for default store image
        default_image_path = os.path.join(base_dir, 'static', 'images', 'default-store.jpg')
        if os.path.exists(default_image_path):
            print("✓ Default store image found")
        else:
            print("✗ Default store image missing")
        
        # Load initial data
        print("\nLoading data...")
        df = load_data()
        if not df.empty:
            print(f"✓ Loaded {len(df)} records")
            print(f"✓ Found {df['photo'].notna().sum()} stores with photos")
        else:
            print("✗ No data loaded")
        
        print("\nServer Information:")
        print("------------------")
        print("URL: http://localhost:8080")
        print("Debug mode: Enabled")
        print("Press CTRL+C to stop the server")
        print("============================\n")
        
        # Start the server
        app.run(
            host='0.0.0.0',  # Allow external connections
            port=8080,       # Use port 8080 instead of 5000
            debug=True
        )
    except Exception as e:
        print(f"\n✗ Error starting server: {e}")
        app.logger.error(f"Server startup error: {e}")