CREATE TABLE IF NOT EXISTS movies (
    movie_id TEXT PRIMARY KEY,
    title TEXT,
    genre TEXT,
    release_year TEXT,
    language TEXT,
    content_rating TEXT,
    runtime_minutes TEXT
);

CREATE TABLE IF NOT EXISTS viewers (
    viewer_id TEXT PRIMARY KEY,
    region TEXT,
    country TEXT,
    age_group TEXT,
    subscription_type TEXT,
    device_type TEXT,
    join_date TEXT
);

CREATE TABLE IF NOT EXISTS watch_activity (
    activity_id TEXT PRIMARY KEY,
    viewer_id TEXT,
    movie_id TEXT,
    watch_date TEXT,
    watch_minutes INTEGER,
    completion_rate REAL,
    device_used TEXT,
    FOREIGN KEY (viewer_id) REFERENCES viewers(viewer_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    viewer_id TEXT,
    movie_id TEXT,
    rating INTEGER,
    review_text TEXT,
    sentiment TEXT,
    review_date TEXT,
    FOREIGN KEY (viewer_id) REFERENCES viewers(viewer_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id)
);

CREATE TABLE IF NOT EXISTS marketing_campaigns (
    campaign_id TEXT PRIMARY KEY,
    campaign_name TEXT,
    region TEXT,
    platform TEXT,
    spend_usd REAL,
    impressions INTEGER,
    conversion_rate REAL,
    quarter TEXT
);

CREATE TABLE IF NOT EXISTS regional_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region TEXT,
    quarter TEXT,
    total_watch_hours INTEGER,
    new_subscribers INTEGER,
    churn_rate REAL,
    avg_completion_rate REAL
);

CREATE TABLE IF NOT EXISTS ingestion_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    ingestion_date TEXT,
    status TEXT,
    rows_processed INTEGER,
    errors_detected INTEGER,
    log_message TEXT
);

CREATE TABLE IF NOT EXISTS pdf_chunks_metadata (
    chunk_id TEXT PRIMARY KEY,
    document_name TEXT,
    page_number INTEGER,
    text_content TEXT,
    embedding_id TEXT
);
