#!/usr/bin/env python3
"""
Test script for emoji and status indicator functionality
"""
import locale
from maestro.tui.widgets.status_indicators import (
    get_status_emoji, 
    get_status_indicator, 
    get_priority_style, 
    get_progress_bar,
    supports_emoji
)

def test_emoji_support():
    """Test emoji support detection"""
    print("Testing emoji support...")
    print(f"System locale: {locale.getpreferredencoding()}")
    print(f"Supports emoji: {supports_emoji()}")
    print()

def test_status_indicators():
    """Test status indicator functionality"""
    print("Testing status indicators...")
    statuses = ['done', 'in_progress', 'planned', 'proposed']
    
    for status in statuses:
        emoji = get_status_emoji(status)
        indicator = get_status_indicator(status)
        print(f"Status: {status:<12} | Emoji: {emoji} | Indicator: {indicator}")
    print()

def test_priority_styles():
    """Test priority styling"""
    print("Testing priority styles...")
    priorities = ['P0', 'P1', 'P2', 'invalid']
    
    for priority in priorities:
        style = get_priority_style(priority)
        print(f"Priority: {priority:<8} | Style: {style}")
    print()

def test_progress_bars():
    """Test progress bar functionality"""
    print("Testing progress bars...")
    percentages = [0, 25, 50, 75, 100]
    
    for pct in percentages:
        bar = get_progress_bar(pct)
        print(f"Progress: {pct:>3}% | {bar}")
    print()

if __name__ == "__main__":
    print("Maestro Status Indicators Test")
    print("=" * 40)
    
    test_emoji_support()
    test_status_indicators()
    test_priority_styles()
    test_progress_bars()
    
    print("Test completed successfully!")