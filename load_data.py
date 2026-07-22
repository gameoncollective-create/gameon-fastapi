import csv
import os
from typing import List, Dict

def load_csv(filename: str) -> List[Dict]:
    """Load data from CSV file"""
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                for key, value in row.items():
                    if key in ['id', 'team_id', 'goals', 'assists', 'appearances', 
                               'played', 'won', 'drawn', 'lost', 'gd', 'points', 
                               'gf', 'ga', 'position']:
                        try:
                            row[key] = int(value) if value else 0
                        except ValueError:
                            row[key] = 0
                    elif key in ['player_rating']:
                        try:
                            row[key] = float(value) if value else 0.0
                        except ValueError:
                            row[key] = 0.0
                data.append(row)
        print(f"✅ Loaded {len(data)} records from {filename}")
        return data
    except FileNotFoundError:
        print(f"⚠️ File not found: {filename}")
        return []
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return []

def save_csv(filename: str, data: List[Dict], fieldnames: List[str]):
    """Save data to CSV file"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"✅ Saved {len(data)} records to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")
        return False
    