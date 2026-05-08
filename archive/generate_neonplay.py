import csv
import random
import os
from datetime import datetime, timedelta

output_dir = r"c:\Users\shrav\Desktop\12 week thing\futures-first\startup_messy_data"
os.makedirs(output_dir, exist_ok=True)

# 1. movies.csv
print("Generating movies.csv...")
base_titles = ["Galaxy Burn", "Shadow Circuit", "HarborLine", "Last Orbit", "Neon Streets"]
genres_messy = ["SciFi", "Sci-Fi", "sci-fi", "Thriller", "thriller", "Drama", "DRAMA", "Fantasy", "Action"]
languages = ["English", "Spanish", "Korean", "Japanese", "EN", "ES"]
ratings = ["PG-13", "R", "TV-MA", "TV-14", ""]

movies = []
sci_fi_movie_ids = []
for i in range(1, 61):
    movie_id = f"MOV{i:03d}"
    
    if i <= 5:
        title = base_titles[i-1]
        genre = random.choice(["SciFi", "Sci-Fi", "sci-fi"]) if "Burn" in title or "Circuit" in title or "Orbit" in title else "Drama"
    else:
        title = f"Project {random.choice(['Alpha', 'beta', 'GAMMA', 'Delta', 'omega', 'Sigma'])} {i}"
        genre = random.choice(genres_messy)
        
    # Inject messiness into title
    if random.random() < 0.1:
        title = title.lower()
    if random.random() < 0.05:
        title = title + " Final"
    if random.random() < 0.05:
        title = "" + title # Encoding issue
        
    if genre.lower().replace("-", "") == "scifi":
        sci_fi_movie_ids.append(movie_id)
        
    release_year = random.choice([str(random.randint(2018, 2026)), "", "202x"])
    language = random.choice(languages)
    content_rating = random.choice(ratings)
    runtime_minutes = str(random.randint(85, 160)) if random.random() < 0.95 else ""
    
    movies.append([movie_id, title, genre, release_year, language, content_rating, runtime_minutes])

# Add a duplicate movie
movies.append(["MOV001", "Galaxy Burn Final_v2", "SciFi", "2023", "English", "PG-13", "120"])

with open(os.path.join(output_dir, "movies.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["movie_id", "title", "genre", "release_year", "language", "content_rating", "runtime_minutes"])
    writer.writerows(movies)

# 2. viewers.csv
print("Generating viewers.csv...")
regions_messy = ["APAC", "Apac", "Asia Pacific", "North America", "NA", "Europe", "EU", "LATAM"]
countries = ["USA", "Japan", "South Korea", "UK", "Germany", "Brazil", "India", "Australia"]
age_groups = ["18-24", "25-34", "35-44", "45-54", "55+", ""]
sub_types = ["Basic", "Standard", "Premium", "premium", "BASIC"]
devices_messy = ["Mobile", "mobile", "MOBILE", "Smart TV", "Desktop", "Tablet", ""]

viewers = []
apac_viewer_ids = []
for i in range(1, 1501):
    viewer_id = f"VWR{i:04d}"
    region = random.choice(regions_messy)
    if region.lower() in ["apac", "asia pacific"]:
        apac_viewer_ids.append(viewer_id)
    country = random.choice(countries)
    age = random.choice(age_groups)
    sub = random.choice(sub_types)
    
    device = random.choice(devices_messy)
    if region.lower() in ["apac", "asia pacific"] and random.random() < 0.8:
        device = random.choice(["Mobile", "mobile", "MOBILE", "iphone", "android"])
        
    # Join date messiness
    dt = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))
    r_date = random.random()
    if r_date < 0.9:
        join_date = dt.strftime("%Y-%m-%d")
    elif r_date < 0.95:
        join_date = dt.strftime("%Y/%m/%d")
    else:
        join_date = dt.strftime("%d-%m-%Y") # Malformed for standard ISO
        
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
devices_watch = ["iphone", "iPhone", "Mobile", "android", "SmartTV", "smart tv", "Desktop", "web"]

def get_watch_time():
    hour = random.choices([random.randint(0, 4), random.randint(18, 23), random.randint(5, 17)], weights=[0.2, 0.6, 0.2])[0]
    minute = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:00"

activity_counter = 1
for i in range(1, 15001):
    activity_id = f"ACT{activity_counter:05d}"
    if random.random() < 0.01: # Duplicate activity ID
        pass
    else:
        activity_counter += 1
        
    viewer_id = random.choice(list(viewer_dict.keys()))
    region = viewer_dict[viewer_id]["region"]
    
    # Missing movie ID
    if random.random() < 0.02:
        movie_id = ""
    else:
        if region.lower() in ["apac", "asia pacific"] and random.random() < 0.7:
            movie_id = random.choice(sci_fi_movie_ids) if sci_fi_movie_ids else random.choice(movie_ids)
        else:
            movie_id = random.choice(movie_ids)
        
    watch_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
    watch_date_time = f"{watch_date} {get_watch_time()}"
    
    if region.lower() in ["apac", "asia pacific"] and movie_id in sci_fi_movie_ids:
        completion_rate = random.randint(80, 100)
    else:
        completion_rate = random.randint(10, 100)
        
    # Impossible completion rates
    if random.random() < 0.01:
        completion_rate = random.choice([105, 999, -10])
        
    watch_minutes = int(120 * (completion_rate / 100.0)) if completion_rate > 0 and completion_rate <= 100 else 150
    device_used = random.choice(devices_watch)
    
    activity.append([activity_id, viewer_id, movie_id, watch_date_time, watch_minutes, completion_rate, device_used])

with open(os.path.join(output_dir, "watch_activity.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["activity_id", "viewer_id", "movie_id", "watch_date", "watch_minutes", "completion_rate", "device_used"])
    writer.writerows(activity)

# 4. reviews.csv
print("Generating reviews.csv...")
reviews = []
review_texts = [
    "THIS SHOW IS INSANE 🔥",
    "ending felt rushed tbh",
    "subtitles broken again",
    "音楽 was good",
    "galaxy burn is the best thing ever 💯",
    "idk why people like this",
    "so good!",
    "meh",
    "why is the app crashing?",
    "love it",
    "terrible pacing ngl"
]

for i in range(1, 2501):
    review_id = f"REV{i:04d}"
    viewer_id = random.choice(list(viewer_dict.keys()))
    movie_id = random.choice(movie_ids)
    
    rating = random.randint(1, 5)
    
    text = random.choice(review_texts)
    
    # Missing text
    if random.random() < 0.05:
        text = ""
        
    # Malformed export
    if random.random() < 0.02:
        text = random.choice(["ERROR_EXPORT_ROW", "#### temp ####", "NaN", "NULL"])
        
    if rating >= 4:
        sentiment = "Positive"
    elif rating == 3:
        sentiment = "Neutral"
    else:
        sentiment = "Negative"
        
    # Inconsistent sentiment
    if random.random() < 0.05:
        sentiment = sentiment.lower()
        
    review_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")
    reviews.append([review_id, viewer_id, movie_id, rating, text, sentiment, review_date])

with open(os.path.join(output_dir, "reviews.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["review_id", "viewer_id", "movie_id", "rating", "review_text", "sentiment", "review_date"])
    writer.writerows(reviews)

# 5. marketing_spend.csv
print("Generating marketing_spend.csv...")
marketing = []
platforms_messy = ["TikTok", "tiktok", "Tik Tok", "Instagram Reels", "IG Reels", "YouTube Shorts", "YT", "Google Ads", "Connected TV"]
campaign_names = ["burn_campaign_final", "burnCampaign_v2", "q2growth_USETHIS", "creator_collab_scifi", "generic_ad_1"]

for i in range(1, 61):
    campaign_id = f"CAM{i:03d}"
    platform = random.choice(platforms_messy)
    region = random.choice(regions_messy)
    
    if i <= 5:
        campaign_name = campaign_names[i-1]
    else:
        campaign_name = f"Campaign_{random.choice(['Alpha', 'beta', 'FINAL', 'temp'])}_{random.randint(1,100)}"
        
    spend_usd = random.randint(10000, 500000)
    impressions = int(spend_usd * random.uniform(5, 50))
    
    base_conv = random.uniform(0.01, 0.05)
    if region.lower() in ["apac", "asia pacific"]:
        base_conv *= 1.8
    if region.lower() in ["europe", "eu"]:
        base_conv *= 0.5
        
    conversion_rate = round(base_conv, 4)
    
    # Messy numbers
    if random.random() < 0.05:
        conversion_rate = random.choice([1.5, 9.99]) # 150% or 999%
    if random.random() < 0.05:
        spend_usd = random.choice([-500, 999999999, "NaN"])
        
    quarter = random.choice(["Q2 FY2026", "q2 2026", "2026-Q2"])
    
    marketing.append([campaign_id, campaign_name, region, platform, spend_usd, impressions, conversion_rate, quarter])

with open(os.path.join(output_dir, "marketing_spend.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["campaign_id", "campaign_name", "region", "platform", "spend_usd", "impressions", "conversion_rate", "quarter"])
    writer.writerows(marketing)

# 6. regional_performance.csv
print("Generating regional_performance.csv...")
reg_perf = []
perf_regions = ["APAC", "Asia Pacific", "North America", "NA", "Europe", "EU", "LATAM"]

for region in perf_regions:
    quarter = random.choice(["Q2 FY2026", "q2 2026"])
    if region.lower() in ["apac", "asia pacific"]:
        total_watch_hours = random.randint(5000000, 8000000)
        new_subs = random.randint(100000, 200000)
        churn_rate = round(random.uniform(0.02, 0.04), 4)
        avg_completion = round(random.uniform(75.0, 90.0), 2)
    elif region.lower() in ["europe", "eu"]:
        total_watch_hours = random.randint(1000000, 2000000)
        new_subs = random.randint(10000, 30000)
        churn_rate = round(random.uniform(0.06, 0.10), 4)
        avg_completion = round(random.uniform(40.0, 60.0), 2)
    else:
        total_watch_hours = random.randint(2000000, 5000000)
        new_subs = random.randint(30000, 80000)
        churn_rate = round(random.uniform(0.04, 0.07), 4)
        avg_completion = round(random.uniform(55.0, 75.0), 2)
        
    # Messy formatting
    if random.random() < 0.3:
        avg_completion = round(avg_completion, 5) # Too many decimals
    if random.random() < 0.1:
        total_watch_hours = "" # Missing value
        
    reg_perf.append([region, quarter, total_watch_hours, new_subs, churn_rate, avg_completion])

with open(os.path.join(output_dir, "regional_performance.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["region", "quarter", "total_watch_hours", "new_subscribers", "churn_rate", "avg_completion_rate"])
    writer.writerows(reg_perf)

print("All startup datasets generated successfully.")
