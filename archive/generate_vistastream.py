import csv
import random
import os
from datetime import datetime, timedelta

output_dir = r"c:\Users\shrav\Desktop\12 week thing\futures-first\enterprise_clean_data"
os.makedirs(output_dir, exist_ok=True)

# 1. movies.csv
print("Generating movies.csv...")
flagships = ["Galactic Dawn: Reborn", "Echo Protocol", "Silent Harbor", "Neon Circuit"]
genres = ["Sci-Fi", "Thriller", "Drama", "Fantasy"]
languages = ["English", "Spanish", "Korean", "Japanese"]
ratings = ["PG-13", "R", "TV-MA", "TV-14"]

movies = []
sci_fi_movie_ids = []
for i in range(1, 61):
    movie_id = f"MOV{i:03d}"
    if i <= 4:
        title = flagships[i-1]
        genre = "Sci-Fi" if i in [1, 2, 4] else "Drama"
    else:
        title = f"Project {random.choice(['Alpha', 'Beta', 'Gamma', 'Delta', 'Omega', 'Sigma'])} {i}"
        genre = random.choice(genres)
    
    if genre == "Sci-Fi":
        sci_fi_movie_ids.append(movie_id)
        
    release_year = random.randint(2018, 2026)
    language = random.choice(languages)
    content_rating = random.choice(ratings)
    runtime_minutes = random.randint(85, 160)
    movies.append([movie_id, title, genre, release_year, language, content_rating, runtime_minutes])

with open(os.path.join(output_dir, "movies.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["movie_id", "title", "genre", "release_year", "language", "content_rating", "runtime_minutes"])
    writer.writerows(movies)

# 2. viewers.csv
print("Generating viewers.csv...")
regions = ["APAC", "North America", "Europe", "LATAM"]
countries = {
    "APAC": ["Japan", "South Korea", "India", "Australia", "Singapore"],
    "North America": ["USA", "Canada", "Mexico"],
    "Europe": ["UK", "Germany", "France", "Spain", "Italy"],
    "LATAM": ["Brazil", "Argentina", "Chile", "Colombia"]
}
age_groups = ["18-24", "25-34", "35-44", "45-54", "55+"]
sub_types = ["Basic", "Standard", "Premium"]
devices = ["Mobile", "Smart TV", "Desktop", "Tablet"]

viewers = []
apac_viewer_ids = []
for i in range(1, 1501):
    viewer_id = f"VWR{i:04d}"
    region = random.choice(regions)
    if region == "APAC":
        apac_viewer_ids.append(viewer_id)
    country = random.choice(countries[region])
    age = random.choice(age_groups)
    sub = random.choice(sub_types)
    device = random.choice(devices)
    if region == "APAC" and random.random() < 0.7:
        device = "Mobile" # Mobile dominates APAC
        
    join_date = (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))).strftime("%Y-%m-%d")
    viewers.append([viewer_id, region, country, age, sub, device, join_date])

with open(os.path.join(output_dir, "viewers.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["viewer_id", "region", "country", "age_group", "subscription_type", "device_type", "join_date"])
    writer.writerows(viewers)

# 3. watch_activity.csv
print("Generating watch_activity.csv...")
activity = []
viewer_dict = {v[0]: {"region": v[1], "device": v[5]} for v in viewers}
movie_ids = [m[0] for m in movies]

# Evening watch spikes, serial binge
def get_watch_time():
    hour = random.choices([random.randint(0, 16), random.randint(17, 23)], weights=[0.3, 0.7])[0]
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:00"

for i in range(1, 20001):
    activity_id = f"ACT{i:05d}"
    viewer_id = random.choice(list(viewer_dict.keys()))
    
    # APAC + Sci-Fi strong engagement
    region = viewer_dict[viewer_id]["region"]
    if region == "APAC" and random.random() < 0.6:
        movie_id = random.choice(sci_fi_movie_ids) if sci_fi_movie_ids else random.choice(movie_ids)
    else:
        movie_id = random.choice(movie_ids)
        
    watch_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
    watch_date_time = f"{watch_date} {get_watch_time()}"
    
    if region == "APAC" and movie_id in sci_fi_movie_ids:
        completion_rate = random.randint(80, 100)
    else:
        completion_rate = random.randint(10, 100)
        
    watch_minutes = int(120 * (completion_rate / 100.0))
    device_used = viewer_dict[viewer_id]["device"]
    
    activity.append([activity_id, viewer_id, movie_id, watch_date_time, watch_minutes, completion_rate, device_used])

with open(os.path.join(output_dir, "watch_activity.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["activity_id", "viewer_id", "movie_id", "watch_date", "watch_minutes", "completion_rate", "device_used"])
    writer.writerows(activity)

# 4. reviews.csv
print("Generating reviews.csv...")
reviews = []
good_texts = ["Strong pacing and high production quality.", "An absolute masterpiece.", "Loved the character development.", "Will definitely watch again.", "Incredible visual effects."]
neutral_texts = ["It was okay, not great.", "Pacing felt a bit slow.", "Decent watch for a Sunday afternoon.", "Nothing special, but not bad.", "Average movie experience."]
bad_texts = ["Terrible plot and awful acting.", "Waste of time.", "Could not finish it.", "Very disappointing.", "Expected much better."]

for i in range(1, 2501):
    review_id = f"REV{i:04d}"
    viewer_id = random.choice(list(viewer_dict.keys()))
    movie_id = random.choice(movie_ids)
    region = viewer_dict[viewer_id]["region"]
    
    if region == "APAC" and movie_id in sci_fi_movie_ids:
        rating = random.randint(4, 5)
    else:
        rating = random.randint(1, 5)
        
    if rating >= 4:
        text = random.choice(good_texts)
        sentiment = "Positive"
    elif rating == 3:
        text = random.choice(neutral_texts)
        sentiment = "Neutral"
    else:
        text = random.choice(bad_texts)
        sentiment = "Negative"
        
    review_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
    reviews.append([review_id, viewer_id, movie_id, rating, text, sentiment, review_date])

with open(os.path.join(output_dir, "reviews.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["review_id", "viewer_id", "movie_id", "rating", "review_text", "sentiment", "review_date"])
    writer.writerows(reviews)

# 5. marketing_spend.csv
print("Generating marketing_spend.csv...")
marketing = []
platforms = ["TikTok", "Instagram Reels", "YouTube Shorts", "Google Ads", "Connected TV"]
campaign_types = ["Creator Collab", "Generic Ad", "Brand Awareness", "Direct Response"]

for i in range(1, 61):
    campaign_id = f"CAM{i:03d}"
    platform = random.choice(platforms)
    region = random.choice(regions)
    camp_type = random.choice(campaign_types)
    campaign_name = f"{camp_type} - {region} {platform}"
    spend_usd = random.randint(10000, 500000)
    impressions = int(spend_usd * random.uniform(5, 50))
    
    base_conv = random.uniform(0.01, 0.05)
    if region == "APAC":
        base_conv *= 1.5
    if region == "Europe":
        base_conv *= 0.6
    if "Creator Collab" in camp_type:
        base_conv *= 1.4
        
    conversion_rate = round(base_conv, 4)
    quarter = "Q2 FY2026"
    
    marketing.append([campaign_id, campaign_name, region, platform, spend_usd, impressions, conversion_rate, quarter])

with open(os.path.join(output_dir, "marketing_spend.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["campaign_id", "campaign_name", "region", "platform", "spend_usd", "impressions", "conversion_rate", "quarter"])
    writer.writerows(marketing)

# 6. regional_performance.csv
print("Generating regional_performance.csv...")
reg_perf = []
for region in regions:
    quarter = "Q2 FY2026"
    if region == "APAC":
        total_watch_hours = random.randint(5000000, 8000000)
        new_subs = random.randint(100000, 200000)
        churn_rate = round(random.uniform(0.02, 0.04), 4)
        avg_completion = round(random.uniform(75.0, 90.0), 2)
    elif region == "Europe":
        total_watch_hours = random.randint(1000000, 2000000)
        new_subs = random.randint(10000, 30000)
        churn_rate = round(random.uniform(0.06, 0.10), 4)
        avg_completion = round(random.uniform(40.0, 60.0), 2)
    else:
        total_watch_hours = random.randint(2000000, 5000000)
        new_subs = random.randint(30000, 80000)
        churn_rate = round(random.uniform(0.04, 0.07), 4)
        avg_completion = round(random.uniform(55.0, 75.0), 2)
        
    reg_perf.append([region, quarter, total_watch_hours, new_subs, churn_rate, avg_completion])

with open(os.path.join(output_dir, "regional_performance.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["region", "quarter", "total_watch_hours", "new_subscribers", "churn_rate", "avg_completion_rate"])
    writer.writerows(reg_perf)

print("All files generated successfully.")
