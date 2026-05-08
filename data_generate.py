import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Ensure data directory exists
os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/docs', exist_ok=True)

def generate_csv_data():
    np.random.seed(42)
    
    # 1. Movies Metadata
    movies = pd.DataFrame({
        'movie_id': range(1, 11),
        'title': ['Stellar Run', 'Dark Orbit', 'Last Kingdom', 'Comedy Central', 'Urban Legends', 
                  'Ocean Whispers', 'Neon Nights', 'Silent Forest', 'Golden Era', 'Midnight Sun'],
        'genre': ['Sci-Fi', 'Sci-Fi', 'Historical', 'Comedy', 'Horror', 'Documentary', 'Action', 'Thriller', 'Drama', 'Action'],
        'release_date': ['2024-12-20', '2025-01-05', '2024-11-15', '2025-02-10', '2024-10-01', 
                         '2025-03-01', '2025-01-20', '2024-09-12', '2023-12-01', '2025-04-15'],
        'budget_millions': [150, 120, 80, 40, 25, 15, 110, 30, 60, 95]
    })
    movies.to_csv('data/raw/movies.csv', index=False)

    # 2. Viewers Data
    viewers = pd.DataFrame({
        'viewer_id': range(1001, 1051),
        'age_group': np.random.choice(['18-24', '25-34', '35-50', '50+'], 50),
        'subscription_tier': np.random.choice(['Basic', 'Premium', 'Ultra'], 50),
        'primary_city': np.random.choice(['Mumbai', 'Delhi', 'New York', 'London', 'Tokyo'], 50)
    })
    viewers.to_csv('data/raw/viewers.csv', index=False)

    # 3. Regional Performance
    regions = ['Mumbai', 'Delhi', 'New York', 'London', 'Tokyo']
    regional_perf = []
    for m_id in movies['movie_id']:
        for city in regions:
            engagement = np.random.randint(10, 100)
            # Injecting the "Mumbai" trend for Stellar Run
            if m_id == 1 and city == 'Mumbai':
                engagement = 95 
            regional_perf.append([m_id, city, engagement, np.random.randint(1000, 5000)])
            
    df_regional = pd.DataFrame(regional_perf, columns=['movie_id', 'city', 'engagement_score', 'active_viewers'])
    df_regional.to_csv('data/raw/regional_performance.csv', index=False)

    # 4. Watch Activity (Time series)
    dates = [datetime(2025, 4, 1) + timedelta(days=x) for x in range(30)]
    activity = []
    for d in dates:
        for m_id in movies['movie_id']:
            views = np.random.randint(1000, 5000)
            if m_id == 1: # Stellar Run Growth
                days_passed = (d - datetime(2025, 4, 1)).days
                views = 5000 + (days_passed * 500)
            activity.append([d.strftime('%Y-%m-%d'), m_id, views])
            
    df_activity = pd.DataFrame(activity, columns=['date', 'movie_id', 'daily_views'])
    df_activity.to_csv('data/raw/watch_activity.csv', index=False)

    # 5. Reviews (Sentiment Signal)
    reviews_data = []
    for m_id in movies['movie_id']:
        for _ in range(5): # 5 reviews per movie
            rating = np.random.randint(1, 6)
            if m_id == 1: rating = 5 # Stellar Run is loved
            if m_id == 4: rating = np.random.randint(1, 3) # Comedy Central is struggling
            reviews_data.append([m_id, rating, "Review comment placeholder text."])
    
    df_reviews = pd.DataFrame(reviews_data, columns=['movie_id', 'rating', 'comment'])
    df_reviews.to_csv('data/raw/reviews.csv', index=False)

    # 6. Marketing Spend
    marketing = []
    for m_id in movies['movie_id']:
        base_spend = np.random.randint(1, 10)
        if m_id == 1: base_spend = 25 # High spend for Stellar Run
        marketing.append([m_id, base_spend, base_spend * 0.2]) # Spend and ROI
    
    df_marketing = pd.DataFrame(marketing, columns=['movie_id', 'spend_millions', 'social_media_conversion_rate'])
    df_marketing.to_csv('data/raw/marketing_spend.csv', index=False)
    
    print("All 6 CSVs generated successfully in data/raw/")

def generate_pdf_content():
    reports = {
        "quarterly_executive_report.txt": """
        EXECUTIVE SUMMARY - Q2 2025
        Stellar Run has exceeded all performance benchmarks this quarter. 
        The surge is primarily attributed to a massive viral marketing campaign in the APAC region, 
        specifically targeting metro cities like Mumbai. High ROI was noted on social media conversions.
        Meanwhile, Comedy performance remains weak across the board. Comedy Central failed to capture 
        the 18-24 demographic, likely due to oversaturation in the streaming market.
        """,
        "audience_behavior_report.txt": """
        AUDIENCE INSIGHTS 2025
        Viewers of Sci-Fi titles (Stellar Run, Dark Orbit) show a 60% higher retention rate 
        compared to Comedy viewers. 
        The 'Last Kingdom' audience is predominantly older (35-50), while 'Neon Nights' 
        is trending with Gen Z.
        """
    }
    
    for filename, content in reports.items():
        with open(f'data/docs/{filename}', 'w') as f:
            f.write(content)
    
    print("Report content generated in data/docs/")

if __name__ == "__main__":
    generate_csv_data()
    generate_pdf_content()