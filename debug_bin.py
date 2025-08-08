#!/usr/bin/env python3
"""
Debug script to analyze what's in the .bin log file
"""
import sys
import os
from pymavlink import mavutil

def analyze_bin_file(bin_path):
    if not os.path.isfile(bin_path):
        print(f'Bin dosyası bulunamadı: {bin_path}')
        return
    
    print(f'Analyzing: {bin_path}')
    mlog = mavutil.mavlink_connection(bin_path)
    
    message_types = {}
    sample_messages = {}
    total_messages = 0
    
    while True:
        msg = mlog.recv_match(blocking=False)
        if msg is None:
            break
        
        total_messages += 1
        msg_type = msg.get_type()
        
        # Count message types
        if msg_type in message_types:
            message_types[msg_type] += 1
        else:
            message_types[msg_type] = 1
            # Store a sample of the first occurrence
            if len(sample_messages) < 20:  # Limit to first 20 different types
                sample_messages[msg_type] = msg
        
        if total_messages % 10000 == 0:
            print(f'Processed {total_messages} messages...')
    
    print(f'\nTotal messages processed: {total_messages}')
    print(f'Unique message types: {len(message_types)}')
    print('\nMessage type counts (top 20):')
    
    # Sort by count and show top 20
    sorted_types = sorted(message_types.items(), key=lambda x: x[1], reverse=True)
    for msg_type, count in sorted_types[:20]:
        print(f'  {msg_type}: {count}')
    
    print('\nSample message details (first few types):')
    for msg_type, msg in list(sample_messages.items())[:10]:
        print(f'\n--- {msg_type} ---')
        msg_dict = msg.to_dict()
        # Show just the first few fields to avoid spam
        shown = 0
        for key, value in msg_dict.items():
            if shown >= 8:  # Limit to 8 fields per message type
                print('  ...')
                break
            print(f'  {key}: {value}')
            shown += 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python debug_bin.py logfile.bin')
        sys.exit(1)
    
    bin_path = sys.argv[1]
    analyze_bin_file(bin_path)
