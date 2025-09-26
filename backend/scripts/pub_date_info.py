import pandas as pd

# Load your CSV
df = pd.read_csv("/home/ec2-user/PMo/backend/scripts/pubmed_csvs/pubmed25n1261.csv")

# Convert published_date column to datetime
df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")

# Drop rows where published_date could not be parsed
df = df.dropna(subset=["published_date"])

# Find oldest and most recent published dates
oldest = df["published_date"].min()
newest = df["published_date"].max()

# Get paper IDs (and titles) for those dates
oldest_papers = df.loc[df["published_date"] == oldest, ["paper_id"]]
newest_papers = df.loc[df["published_date"] == newest, ["paper_id"]]

print("Oldest published date:", oldest.date())
print(oldest_papers.to_string(index=False))

print("\nMost recent published date:", newest.date())
print(newest_papers.to_string(index=False))
