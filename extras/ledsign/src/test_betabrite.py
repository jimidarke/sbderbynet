"""
BetaBrite Library Test Script

This script tests the BetaBrite library functions on actual hardware.
Run on ESP32 with BetaBrite sign connected via serial.

Usage:
    1. Upload betabrite.py and this file to ESP32
    2. Connect ESP32 TX (GPIO17) to BetaBrite RX via MAX3232
    3. Run: import test_betabrite
    4. Call test functions: test_betabrite.test_basic()

Hardware Setup:
    ESP32 GPIO17 (TX2) --> MAX3232 T1IN --> T1OUT --> BetaBrite RX (Pin 4)
    ESP32 GND --> MAX3232 GND --> BetaBrite GND (Pin 1 or 6)
"""

import time

# For ESP32 MicroPython
try:
    from machine import UART, Pin
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    print("Not running on MicroPython - using mock serial")

from betabrite import (
    BetaBrite, Mode, Color, CharSet, Position, Speed, Effect,
    FileLabel, parse_display_config
)


# =============================================================================
# Serial Setup
# =============================================================================

def get_serial():
    """Get serial/UART object for BetaBrite communication"""
    if MICROPYTHON:
        # ESP32 UART2: TX=GPIO17, RX=GPIO16
        uart = UART(2, baudrate=9600, tx=17, rx=16)
        return uart
    else:
        # Mock serial for desktop testing
        class MockSerial:
            def write(self, data):
                print(f"[MOCK] Sending {len(data)} bytes: {repr(data[:50])}...")
        return MockSerial()


# Global sign instance
_sign = None

def get_sign():
    """Get or create BetaBrite sign instance"""
    global _sign
    if _sign is None:
        serial = get_serial()
        _sign = BetaBrite(serial)
    return _sign


# =============================================================================
# Basic Tests
# =============================================================================

def test_basic():
    """Test basic text display"""
    sign = get_sign()
    print("Testing basic text display...")

    sign.write_text("Hello World!", mode='hold', color='green')
    print("  Sent: Hello World! (hold, green)")
    time.sleep(3)

    sign.write_text("BetaBrite Test", mode='hold', color='amber')
    print("  Sent: BetaBrite Test (hold, amber)")
    time.sleep(3)

    print("Basic test complete!")


def test_modes():
    """Test different display modes"""
    sign = get_sign()
    print("Testing display modes...")

    modes_to_test = [
        ('hold', 'Static Hold'),
        ('flash', 'Flashing'),
        ('scroll', 'Scrolling Text - This message scrolls across'),
        ('roll_up', 'Roll Up'),
        ('roll_left', 'Roll Left'),
        ('wipe_in', 'Wipe In'),
    ]

    for mode, text in modes_to_test:
        print(f"  Mode: {mode}")
        sign.write_text(text, mode=mode, color='green')
        time.sleep(4)

    print("Mode test complete!")


def test_colors():
    """Test different colors"""
    sign = get_sign()
    print("Testing colors...")

    colors = ['red', 'green', 'amber', 'yellow', 'orange', 'rainbow1']

    for color in colors:
        print(f"  Color: {color}")
        sign.write_text(f"Color: {color.upper()}", mode='hold', color=color)
        time.sleep(2)

    print("Color test complete!")


def test_charsets():
    """Test different character sets"""
    sign = get_sign()
    print("Testing character sets...")

    charsets = [
        ('5high', 'Small'),
        ('7high', 'Medium'),
        ('10high', 'Large'),
        ('7highfancy', 'Fancy'),
    ]

    for charset, label in charsets:
        print(f"  Charset: {charset}")
        sign.write_text(label, mode='hold', color='green', charset=charset)
        time.sleep(3)

    print("Character set test complete!")


def test_priority():
    """Test priority message (interrupts rotation)"""
    sign = get_sign()
    print("Testing priority messages...")

    # Write some normal text first
    sign.write_text("Normal Display", mode='hold', color='green')
    print("  Normal display set")
    time.sleep(2)

    # Send priority message
    sign.write_priority("PRIORITY!", color='red')
    print("  Priority message sent")
    time.sleep(4)

    # Cancel priority
    sign.cancel_priority()
    print("  Priority canceled")
    time.sleep(2)

    print("Priority test complete!")


def test_special_effects():
    """Test special effects"""
    sign = get_sign()
    print("Testing special effects...")

    effects = ['twinkle', 'sparkle', 'snow', 'starburst']

    for effect in effects:
        print(f"  Effect: {effect}")
        sign.write_text(f"Effect: {effect}", mode='special',
                       color='rainbow1', effect=effect)
        time.sleep(4)

    print("Special effects test complete!")


def test_convenience():
    """Test convenience methods"""
    sign = get_sign()
    print("Testing convenience methods...")

    styles = ['normal', 'success', 'warning', 'error', 'info']

    for style in styles:
        print(f"  Style: {style}")
        sign.show_message(f"Style: {style}", style=style)
        time.sleep(3)

    # Test scrolling
    print("  Scrolling text...")
    sign.show_scrolling("This is a long scrolling message for testing")
    time.sleep(6)

    # Test alerts
    print("  Alert levels...")
    for level in ['info', 'warning', 'critical']:
        sign.show_alert(f"Alert: {level}", level=level)
        time.sleep(3)

    print("Convenience methods test complete!")


def test_json_config():
    """Test parsing JSON display_config"""
    print("Testing JSON config parsing...")

    # Simulate config from MQTT message
    config = {
        "mode": "flash",
        "mode_code": "c",
        "color": "red",
        "color_code": "1",
        "character_set": "10high",
        "charset_code": "6",
        "position": "fill",
        "position_code": "0",
        "speed": 4,
        "speed_code": "\\030"
    }

    args = parse_display_config(config)
    print(f"  Parsed config: {args}")

    sign = get_sign()
    sign.write_text("JSON Config Test", **args)
    time.sleep(3)

    print("JSON config test complete!")


# =============================================================================
# Derby-Specific Tests
# =============================================================================

def test_derby_starter():
    """Test starter sign messages"""
    sign = get_sign()
    print("Testing starter sign displays...")

    # System ready
    sign.write_text("SYSTEM READY", mode='hold', color='green', charset='10high')
    print("  SYSTEM READY")
    time.sleep(3)

    # Not ready (timer offline)
    sign.write_text("LANE 2 OFFLINE", mode='flash', color='red', charset='10high')
    print("  LANE 2 OFFLINE")
    time.sleep(3)

    # Race staged
    sign.write_text("RACE STAGED", mode='flash', color='green', charset='10high')
    print("  RACE STAGED")
    time.sleep(3)

    # Race in progress
    sign.write_text("RACING", mode='hold', color='amber', charset='10high')
    print("  RACING")
    time.sleep(3)

    print("Starter sign test complete!")


def test_derby_usher():
    """Test usher sign messages"""
    sign = get_sign()
    print("Testing usher sign displays...")

    # Racer assignment
    racers = [
        ("#42 JohnS", "green"),
        ("#17 MaryJ", "green"),
        ("#88 BillyT", "green"),
    ]

    for racer, color in racers:
        sign.write_text(racer, mode='hold', color=color, charset='7high')
        print(f"  {racer}")
        time.sleep(3)

    print("Usher sign test complete!")


def test_derby_finish():
    """Test finish line time displays"""
    sign = get_sign()
    print("Testing finish line displays...")

    # Race times in mm:ss.nnn format
    times = ["00:28.456", "00:31.234", "00:29.891", "DNF"]

    for race_time in times:
        sign.write_text(race_time, mode='hold', color='green', charset='10high')
        print(f"  Time: {race_time}")
        time.sleep(3)

    print("Finish line test complete!")


def test_derby_sponsor():
    """Test sponsor rotation"""
    sign = get_sign()
    print("Testing sponsor displays...")

    sponsors = [
        "Thanks to ACME Racing!",
        "Local Pizza Co - Best in town!",
        "Visit cityautobody.com",
    ]

    for sponsor in sponsors:
        sign.write_text(sponsor, mode='scroll', color='rainbow1',
                       charset='7high', speed=2)
        print(f"  {sponsor[:30]}...")
        time.sleep(5)

    print("Sponsor test complete!")


def test_emergency():
    """Test emergency broadcast"""
    sign = get_sign()
    print("Testing emergency broadcast...")

    # Emergency message
    sign.write_priority(
        "MISSING CHILD - BLUE SHIRT",
        mode='flash',
        color='red',
        charset='10high',
        speed=5
    )
    print("  Emergency broadcast sent")
    time.sleep(5)

    # Clear emergency
    sign.cancel_priority()
    print("  Emergency cleared")
    time.sleep(2)

    print("Emergency test complete!")


# =============================================================================
# Run All Tests
# =============================================================================

def run_all():
    """Run all tests in sequence"""
    print("=" * 50)
    print("BetaBrite Library Test Suite")
    print("=" * 50)

    tests = [
        test_basic,
        test_colors,
        test_charsets,
        test_modes,
        test_priority,
        test_convenience,
        test_json_config,
        test_derby_starter,
        test_derby_usher,
        test_derby_finish,
        test_derby_sponsor,
        test_emergency,
    ]

    for test_func in tests:
        print()
        try:
            test_func()
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(2)

    print()
    print("=" * 50)
    print("All tests complete!")
    print("=" * 50)


# =============================================================================
# Quick Display Functions (for interactive use)
# =============================================================================

def msg(text, color='green'):
    """Quick message display"""
    get_sign().write_text(text, mode='hold', color=color)


def alert(text):
    """Quick alert display"""
    get_sign().write_priority(text, mode='flash', color='red')


def clear():
    """Clear priority and show ready"""
    sign = get_sign()
    sign.cancel_priority()
    sign.write_text("READY", mode='hold', color='green')


def scroll(text):
    """Quick scrolling message"""
    get_sign().show_scrolling(text)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    print("BetaBrite Test Module")
    print("---------------------")
    print("Quick functions: msg(text), alert(text), clear(), scroll(text)")
    print("Tests: test_basic(), test_colors(), test_modes(), run_all()")
    print()

    if MICROPYTHON:
        print("Running on MicroPython - hardware ready")
    else:
        print("Running on desktop - using mock serial")
