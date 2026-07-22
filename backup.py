#!/usr/bin/env python3
"""
Backup script for GameOn Collective data
Run: python backup.py
"""

import csv
import os
import shutil
from datetime import datetime

def backup_data():
    """Create a backup of all data files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'backups/{timestamp}'
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Copy all CSV files
    data_files = ['players.csv', 'teams.csv', 'featured_players.csv']
    for file in data_files:
        src = f'data/{file}'
        dst = f'{backup_dir}/{file}'
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"✅ Backed up: {file}")
    
    print(f"\n📁 Backup complete: {backup_dir}")
    return backup_dir

if __name__ == '__main__':
    backup_data()
    