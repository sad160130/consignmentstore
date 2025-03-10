from flask import Flask, render_template, request, redirect, url_for, Response, make_response, send_from_directory
import pandas as pd
from slugify import slugify
from datetime import datetime
from collections import defaultdict
import logging
import shutil
import sys
import os

# Initialize Flask app with explicit template and static paths
app = Flask(__name__, 
           template_folder=os.path.abspath('templates'),
           static_folder=os.path.abspath('static'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def ensure_data_directory():
    """Create data directory if it doesn't exist"""
    data_dir = os.path.abspath('data')
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            print(f"Created data directory at: {data_dir}")
        except Exception as e:
            print(f"Error creating data directory: {str(e)}")

def find_excel_file():
    """Search for the Excel file in various locations"""
    possible_paths = [
        os.path.join('data', 'SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx'),
        'SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx',
        os.path.join('..', 'SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx'),
        r'C:\Users\sanke\Downloads\SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx',
        r'C:\Users\sanke\Downloads\Directory Project\SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx',
        r'C:\Users\sanke\Downloads\Directory Project\consignment-directory\data\SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx'
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        print(f"Checking for Excel file at: {abs_path}")
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'rb') as f:
                    f.read(1024)
                print(f"Found valid Excel file at: {abs_path}")
                return abs_path
            except Exception as e:
                print(f"Found file at {abs_path} but couldn't read it: {str(e)}")
                continue
    return None

def load_data():
    """Load and process the Excel data"""
    try:
        ensure_data_directory()
        file_path = find_excel_file()
        
        if not file_path:
            print("\nError: Could not find a readable Excel file.")
            print("\nPlease follow these steps:")
            print("1. Download a fresh copy of the Excel file")
            print("2. Place it in the 'data' folder at:")
            print(f"   {os.path.abspath('data')}")
            print("3. Make sure the file name is exactly:")
            print("   SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx")
            return None

        print(f"Loading data from: {file_path}")
        df = pd.read_excel(file_path, engine='openpyxl')
        
        if df.empty:
            print("Error: Excel file is empty")
            return None

        # Clean and convert data types
        df = df.fillna('')
        for col in df.columns:
            df[col] = df[col].apply(safe_str)

        # Convert numeric columns
        try:
            df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(0.0)
            df['Number of Reviews'] = pd.to_numeric(df['Number of Reviews'], errors='coerce').fillna(0)
        except Exception as e:
            print(f"Warning: Error converting numeric columns: {str(e)}")

        # Generate slugs
        df['slug'] = df['Business Name'].apply(safe_slugify)
        df['city_slug'] = df['City'].apply(safe_slugify)
        df['state_slug'] = df['State'].apply(safe_slugify)

        df = df.sort_values('Number of Reviews', ascending=False)
        print(f"Successfully loaded {len(df)} records")
        return df

    except Exception as e:
        print(f"\nError loading data: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you have the required packages:")
        print("   pip install --upgrade pandas openpyxl")
        print("2. Check if the Excel file is not open in another program")
        print("3. Verify the Excel file is not corrupted")
        return None

def format_description(description):
    """Format description into paragraphs"""
    if pd.isna(description) or not description:
        return []
    
    description = safe_str(description)
    sentences = description.split('. ')
    paragraphs = []
    current_para = []
    char_count = 0
    
    for sentence in sentences:
        if not sentence.strip():
            continue
        if not sentence.endswith('.'):
            sentence += '.'
        if char_count > 250:
            if current_para:
                paragraphs.append(' '.join(current_para))
            current_para = [sentence]
            char_count = len(sentence)
        else:
            current_para.append(sentence)
            char_count += len(sentence)
    
    if current_para:
        paragraphs.append(' '.join(current_para))
    return paragraphs

def process_data(df):
    """Process DataFrame into structured data"""
    if df is None or df.empty:
        logger.error("Cannot process empty DataFrame")
        return {}

    states_data = {}
    for state in df['State'].unique():
        state_df = df[df['State'] == state]
        state_slug = safe_slugify(state)
        
        cities_data = {}
        for city in state_df['City'].unique():
            city_df = state_df[state_df['City'] == city]
            city_slug = safe_slugify(city)
            
            stores = []
            for _, row in city_df.iterrows():
                try:
                    store = {
                        'name': safe_str(row['Business Name']),
                        'address': safe_str(row['Address']),
                        'rating': float(row['Rating']) if pd.notnull(row['Rating']) else 0.0,
                        'review_count': int(row['Number of Reviews']) if pd.notnull(row['Number of Reviews']) else 0,
                        'description_paragraphs': format_description(row['New SEO Description V2']),
                        'slug': safe_slugify(row['Business Name']),
                        'website': safe_str(row['Site']) if row['Site'] else None,
                        'phone': safe_str(row['Phone']) if row['Phone'] else None,
                        'photo': safe_str(row['Photo']) if row['Photo'] else None
                    }
                    stores.append(store)
                except Exception as e:
                    logger.error(f"Error processing store: {str(e)}")
                    continue
            
            cities_data[city_slug] = {
                'name': city,
                'slug': city_slug,
                'store_count': len(stores),
                'stores': sorted(stores, key=lambda x: (-x['rating'], -x['review_count']))
            }
        
        states_data[state_slug] = {
            'name': state,
            'slug': state_slug,
            'store_count': len(state_df),
            'city_count': len(cities_data),
            'cities': cities_data
        }
    
    return states_data

def get_nearby_cities(df, state, city, limit=6):
    """Get nearby cities within the same state"""
    if df is None or df.empty:
        return []
    try:
        state_df = df[df['State'] == state]
        cities = state_df[state_df['City'] != city]['City'].unique()
        city_counts = state_df[state_df['City'].isin(cities)].groupby('City').size()
        nearby_cities = city_counts.sort_values(ascending=False).head(limit)
        return [{'name': safe_str(city), 'slug': safe_slugify(city), 'store_count': count} 
                for city, count in nearby_cities.items()]
    except Exception as e:
        logger.error(f"Error getting nearby cities: {str(e)}")
        return []

# Load data at startup
print("\n=== Starting Consignment Directory Server ===")
print("\nInitializing data...")
df = load_data()
states_data = process_data(df) if df is not None else {}

@app.context_processor
def utility_processor():
    if not df is None and not df.empty:
        try:
            popular_cities = []
            for state_data in states_data.values():
                for city_data in state_data['cities'].values():
                    popular_cities.append({
                        'name': city_data['name'],
                        'state': state_data['name'],
                        'state_slug': state_data['slug'],
                        'city_slug': city_data['slug'],
                        'store_count': city_data['store_count']
                    })
            
            popular_cities.sort(key=lambda x: x['store_count'], reverse=True)
            popular_cities = popular_cities[:12]

            return {
                'states': sorted([{
                    'name': data['name'], 
                    'slug': data['slug'],
                    'store_count': data['store_count']
                } for data in states_data.values()], 
                key=lambda x: x['name']),
                'popular_cities': popular_cities,
                'total_stores': len(df),
                'total_cities': len(df['City'].unique()),
                'total_states': len(df['State'].unique()),
                'current_year': datetime.now().year
            }
        except Exception as e:
            logger.error(f"Error in utility_processor: {str(e)}")
            
    return {
        'states': [],
        'popular_cities': [],
        'total_stores': 0,
        'total_cities': 0,
        'total_states': 0,
        'current_year': datetime.now().year
    }

@app.route('/')
def home():
    states_by_region = defaultdict(list)
    for region, region_states in REGIONS.items():
        for state_data in states_data.values():
            if state_data['name'] in region_states:
                states_by_region[region].append({
                    'name': state_data['name'],
                    'slug': state_data['slug'],
                    'store_count': state_data['store_count'],
                    'city_count': state_data['city_count']
                })
    
    for region in states_by_region:
        states_by_region[region].sort(key=lambda x: x['name'])
    
    return render_template('home.html', states_by_region=states_by_region)

@app.route('/state/<state_name>')
def state(state_name):
    if state_name not in states_data:
        return render_template('404.html'), 404
    
    state_info = states_data[state_name]
    sorted_cities = sorted(
        state_info['cities'].values(),
        key=lambda x: x['store_count'],
        reverse=True
    )
    
    return render_template('state.html', state=state_info, cities=sorted_cities)

@app.route('/state/<state_name>/<city_name>')
def city(state_name, city_name):
    if state_name not in states_data or city_name not in states_data[state_name]['cities']:
        return render_template('404.html'), 404
    
    state_info = states_data[state_name]
    city_info = state_info['cities'][city_name]
    nearby_cities = get_nearby_cities(df, state_info['name'], city_info['name'])
    
    return render_template('city.html',
                         state=state_info,
                         city=city_info,
                         nearby_cities=nearby_cities)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    if not query:
        return redirect(url_for('home'))
    
    results = {'stores': [], 'cities': [], 'states': []}
    
    if df is not None and not df.empty:
        try:
            store_matches = df[df['Business Name'].str.lower().str.contains(query, na=False)]
            for _, row in store_matches.iterrows():
                results['stores'].append({
                    'name': safe_str(row['Business Name']),
                    'city': safe_str(row['City']),
                    'state': safe_str(row['State']),
                    'state_slug': safe_slugify(row['State']),
                    'city_slug': safe_slugify(row['City']),
                    'rating': float(row['Rating']) if pd.notnull(row['Rating']) else 0.0,
                    'review_count': int(row['Number of Reviews']) if pd.notnull(row['Number of Reviews']) else 0
                })
            
            city_matches = df[df['City'].str.lower().str.contains(query, na=False)].drop_duplicates('City')
            state_matches = df[df['State'].str.lower().str.contains(query, na=False)].drop_duplicates('State')
            
            for _, row in city_matches.iterrows():
                results['cities'].append({
                    'name': safe_str(row['City']),
                    'state': safe_str(row['State']),
                    'state_slug': safe_slugify(row['State']),
                    'city_slug': safe_slugify(row['City'])
                })
            
            for _, row in state_matches.iterrows():
                results['states'].append({
                    'name': safe_str(row['State']),
                    'slug': safe_slugify(row['State'])
                })
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
    
    return render_template('search.html', query=query, results=results)

@app.route('/sitemap')
def sitemap():
    """Display HTML sitemap page"""
    return render_template('sitemap.html')

@app.route('/sitemap.xml')
def xml_sitemap():
    """Generate XML sitemap"""
    try:
        base_url = request.url_root.rstrip('/')
        pages = []
        
        # Add static pages
        pages.append({
            'loc': f"{base_url}/",
            'priority': "1.0",
            'changefreq': "daily"
        })
        pages.append({
            'loc': f"{base_url}/about",
            'priority': "0.5",
            'changefreq': "weekly"
        })
        pages.append({
            'loc': f"{base_url}/sitemap",
            'priority': "0.3",
            'changefreq': "weekly"
        })
        
        # Add state and city pages
        if states_data:
            for state_slug, state_info in states_data.items():
                pages.append({
                    'loc': f"{base_url}/state/{state_slug}",
                    'priority': "0.8",
                    'changefreq': "daily"
                })
                
                for city_slug in state_info['cities'].keys():
                    pages.append({
                        'loc': f"{base_url}/state/{state_slug}/{city_slug}",
                        'priority': "0.6",
                        'changefreq': "daily"
                    })
        
        # Generate XML content with proper indentation
        xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_content.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        
        for page in pages:
            xml_content.append(f'''    <url>
        <loc>{page['loc']}</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <changefreq>{page['changefreq']}</changefreq>
        <priority>{page['priority']}</priority>
    </url>''')
        
        xml_content.append('</urlset>')
        
        # Create response with proper headers
        response = make_response('\n'.join(xml_content))
        response.headers['Content-Type'] = 'application/xml'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
        
    except Exception as e:
        logger.error(f"Error generating sitemap: {str(e)}")
        # Return a basic valid XML response in case of error
        error_response = Response(f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{request.url_root.rstrip('/')}/</loc>
        <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
        <priority>1.0</priority>
    </url>
</urlset>''', mimetype='application/xml')
        error_response.headers['X-Content-Type-Options'] = 'nosniff'
        return error_response

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    try:
        return render_template('404.html'), 404
    except Exception as template_error:
        logger.error(f"Error rendering 404 template: {str(template_error)}")
        return "Page not found", 404

if __name__ == '__main__':
    try:
        if df is None or df.empty:
            print("\nError: Could not load data. Please follow these steps:")
            print("\n1. Locate your Excel file 'SEO_Optimized_Consignment_Stores_Sample_Dataset.xlsx'")
            print("2. Make sure it's in one of these locations:")
            print("   - In the 'data' folder of your project")
            print("   - In your Downloads folder")
            print("   - In the project root directory")
            print("\n3. Install required packages:")
            print("   pip install --upgrade pandas openpyxl flask python-slugify")
            print("\n4. Make sure the Excel file is not open in another program")
            print("5. Check file permissions")
            sys.exit(1)

        print(f"\nSuccessfully loaded {len(df)} stores in {len(df['State'].unique())} states")
        print("\nStarting server...")
        
        # Try different ports
        ports = [5000, 8080, 3000]
        for port in ports:
            try:
                print(f"\nTrying port {port}...")
                print(f"You can access the site at:")
                print(f"1. http://127.0.0.1:{port}")
                print(f"2. http://localhost:{port}")
                app.run(host='127.0.0.1', port=port, debug=True)
                break
            except Exception as e:
                print(f"Port {port} is not available: {str(e)}")
                if port == ports[-1]:
                    print("\nNo available ports found. Please try:")
                    print("1. Close other applications that might be using these ports")
                    print("2. Run as administrator")
                    print("3. Check firewall settings")
                    sys.exit(1)
                continue
                
    except Exception as e:
        print(f"\nError starting server: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure all required packages are installed:")
        print("   pip install --upgrade flask pandas python-slugify openpyxl")
        print("2. Try running with: flask run")
        print("3. Check your firewall settings")
        print("4. Try running as administrator")
        sys.exit(1)