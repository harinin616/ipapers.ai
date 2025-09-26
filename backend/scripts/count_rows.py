import csv

file_path = "pubmed_csvs/embed_pubmed25n1272.csv"

with open(file_path, "r", newline="", encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile)
    row_count = sum(1 for row in reader) - 1  # subtract 1 if header exists

print(f"Number of data rows: {row_count}")


