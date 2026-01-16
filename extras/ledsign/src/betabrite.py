"""
BetaBrite LED Sign Controller Library for MicroPython

This library implements the Alpha Protocol for communicating with BetaBrite
and other Alpha-compatible LED signs over serial (RS-232).

Version: 1.0.0
Author: SBDerbyNet Project
License: MIT

Protocol Reference:
- Baud Rate: 9600
- Data Bits: 8
- Parity: None
- Stop Bits: 1
- Flow Control: None

Command Structure:
<NUL><NUL><NUL><NUL><NUL><SOH><ADDR><TYPE_CODE><CMD><STX><DATA><ETX>
"""

# =============================================================================
# Control Characters
# =============================================================================

NUL = '\x00'  # Null - used for synchronization (5 bytes)
SOH = '\x01'  # Start of Header
STX = '\x02'  # Start of Text
ETX = '\x03'  # End of Text
EOT = '\x04'  # End of Transmission
ESC = '\x1b'  # Escape - used for special sequences

# Default sign address (Z = broadcast to all signs)
DEFAULT_ADDRESS = 'Z'

# Sign type code (00 = all sign types)
TYPE_CODE = '00'


# =============================================================================
# Command Types
# =============================================================================

class CommandType:
    """Alpha Protocol command type codes"""
    WRITE_TEXT = 'A'           # Write TEXT file
    READ_TEXT = 'B'            # Read TEXT file
    WRITE_SPECIAL = 'E'        # Write SPECIAL FUNCTION
    READ_SPECIAL = 'F'         # Read SPECIAL FUNCTION
    WRITE_STRING = 'G'         # Write STRING file
    READ_STRING = 'H'          # Read STRING file
    WRITE_SMALL_DOTS = 'I'     # Write SMALL DOTS picture
    READ_SMALL_DOTS = 'J'      # Read SMALL DOTS picture
    WRITE_RGB_DOTS = 'K'       # Write RGB DOTS picture
    READ_RGB_DOTS = 'L'        # Read RGB DOTS picture
    WRITE_LARGE_DOTS = 'M'     # Write LARGE DOTS picture
    READ_LARGE_DOTS = 'N'      # Read LARGE DOTS picture
    WRITE_BULLETIN = 'O'       # Write BULLETIN message


# =============================================================================
# Special Function Labels (for Command Type 'E')
# =============================================================================

class SpecialFunction:
    """Special function command labels"""
    SET_DATE = '"'             # Set current date
    SET_TIME = ' '             # Set current time (space character)
    SET_MEMORY = '$'           # Configure memory
    SET_RUN_SEQUENCE = '.'     # Set text file run sequence
    SPEAKER_CONTROL = '('      # Control speaker
    SET_TIME_FORMAT = ')'      # Set time format
    SET_DAY_OF_WEEK = '*'      # Set day of week
    CLEAR_MEMORY = ';'         # Clear sign memory
    SOFT_RESET = ','           # Soft reset sign
    SET_ADDRESS = '~'          # Set sign address


# =============================================================================
# File Labels (A-Z for standard text files)
# =============================================================================

class FileLabel:
    """Standard file label characters for text storage"""
    # Priority file (interrupts normal rotation)
    PRIORITY = '0'

    # Standard text files A-Z
    FILE_A = 'A'
    FILE_B = 'B'
    FILE_C = 'C'
    FILE_D = 'D'
    FILE_E = 'E'
    FILE_F = 'F'
    FILE_G = 'G'
    FILE_H = 'H'
    FILE_I = 'I'
    FILE_J = 'J'
    FILE_K = 'K'
    FILE_L = 'L'
    FILE_M = 'M'
    FILE_N = 'N'
    FILE_O = 'O'
    FILE_P = 'P'
    FILE_Q = 'Q'
    FILE_R = 'R'
    FILE_S = 'S'
    FILE_T = 'T'
    FILE_U = 'U'
    FILE_V = 'V'
    FILE_W = 'W'
    FILE_X = 'X'
    FILE_Y = 'Y'
    FILE_Z = 'Z'


# =============================================================================
# Display Modes
# =============================================================================

class Mode:
    """Display mode codes - control how text appears on the sign"""

    # Basic modes
    ROTATE = 'a'               # Cycles through text files
    HOLD = 'b'                 # Static display without movement
    FLASH = 'c'                # Text blinks on/off
    SCROLL = 'm'               # Text scrolls horizontally
    AUTO = 'o'                 # Sign determines best display method

    # Roll modes (smooth motion)
    ROLL_UP = 'e'              # Text rolls up from bottom
    ROLL_DOWN = 'f'            # Text rolls down from top
    ROLL_LEFT = 'g'            # Text rolls in from right
    ROLL_RIGHT = 'h'           # Text rolls in from left
    ROLL_IN = 'p'              # Text rolls in from edges
    ROLL_OUT = 'q'             # Text rolls out to edges

    # Wipe modes (reveal effect)
    WIPE_UP = 'i'              # Text wipes upward
    WIPE_DOWN = 'j'            # Text wipes downward
    WIPE_LEFT = 'k'            # Text wipes leftward
    WIPE_RIGHT = 'l'           # Text wipes rightward
    WIPE_IN = 'r'              # Text wipes in from edges
    WIPE_OUT = 's'             # Text wipes out to edges

    # Advanced modes
    COMPRESSED_ROTATE = 't'    # Compact rotation display
    EXPLODE = 'u'              # Text explodes outward
    CLOCK = 'v'                # Time/date display mode
    SPECIAL = 'n'              # Enables special effects

    # Lookup by name
    _BY_NAME = {
        'rotate': 'a', 'hold': 'b', 'flash': 'c', 'scroll': 'm', 'auto': 'o',
        'rollup': 'e', 'roll_up': 'e', 'rolldown': 'f', 'roll_down': 'f',
        'rollleft': 'g', 'roll_left': 'g', 'rollright': 'h', 'roll_right': 'h',
        'rollin': 'p', 'roll_in': 'p', 'rollout': 'q', 'roll_out': 'q',
        'wipeup': 'i', 'wipe_up': 'i', 'wipedown': 'j', 'wipe_down': 'j',
        'wipeleft': 'k', 'wipe_left': 'k', 'wiperight': 'l', 'wipe_right': 'l',
        'wipein': 'r', 'wipe_in': 'r', 'wipeout': 's', 'wipe_out': 's',
        'compressed_rotate': 't', 'compressedrotate': 't',
        'explode': 'u', 'clock': 'v', 'special': 'n'
    }

    @classmethod
    def from_name(cls, name):
        """Get mode code from name string"""
        return cls._BY_NAME.get(name.lower(), cls.HOLD)


# =============================================================================
# Colors
# =============================================================================

class Color:
    """Color codes for text display"""

    # Standard colors
    RED = '1'                  # Bright red - critical alerts, emergencies
    GREEN = '2'                # Bright green - success, normal status
    AMBER = '3'                # Amber/orange - warnings, caution
    DIM_RED = '4'              # Darker red - subdued alerts
    DIM_GREEN = '5'            # Darker green - background status
    BROWN = '6'                # Brown/dark amber - neutral information
    ORANGE = '7'               # Orange - moderate warnings
    YELLOW = '8'               # Bright yellow - attention, information

    # Dynamic colors
    RAINBOW_1 = '9'            # First rainbow pattern - multi-color cycling
    RAINBOW_2 = 'A'            # Second rainbow pattern
    COLOR_MIX = 'B'            # Mixed color pattern - varied display
    AUTO = 'C'                 # Sign determines color automatically

    # Lookup by name
    _BY_NAME = {
        'red': '1', 'green': '2', 'amber': '3', 'dimred': '4', 'dim_red': '4',
        'dimgreen': '5', 'dim_green': '5', 'brown': '6', 'orange': '7',
        'yellow': '8', 'rainbow1': '9', 'rainbow_1': '9', 'rainbow2': 'A',
        'rainbow_2': 'A', 'colormix': 'B', 'color_mix': 'B', 'auto': 'C'
    }

    @classmethod
    def from_name(cls, name):
        """Get color code from name string"""
        return cls._BY_NAME.get(name.lower(), cls.GREEN)

    @classmethod
    def code(cls, color_code):
        """Generate color control sequence: ESC + color_code"""
        return ESC + color_code


# =============================================================================
# Character Sets
# =============================================================================

class CharSet:
    """Character set codes - control text size and style"""

    # Standard heights
    FIVE_HIGH = '1'            # Basic 5-pixel height - small, simple
    FIVE_STROKE = '2'          # 5-pixel stroke font - small, outlined
    SEVEN_HIGH = '3'           # Standard 7-pixel height - medium, clean
    SEVEN_STROKE = '4'         # 7-pixel stroke font - medium, outlined
    SEVEN_HIGH_FANCY = '5'     # Decorative 7-pixel - medium, stylized
    TEN_HIGH = '6'             # Large 10-pixel height - large, bold

    # Enhanced styles
    SEVEN_SHADOW = '7'         # Shadow effect - dimensional
    FULL_HIGH_FANCY = '8'      # Full height decorative - elegant
    FULL_HIGH = '9'            # Full height standard - maximum size
    SEVEN_SHADOW_FANCY = ':'   # Shadow with decoration - ornate

    # Wide character sets
    FIVE_WIDE = ';'            # 5-pixel wide - compact wide
    SEVEN_WIDE = '<'           # 7-pixel wide - standard wide
    SEVEN_WIDE_FANCY = '='     # Decorative wide - stylized wide
    FIVE_WIDE_STROKE = '>'     # 5-pixel wide outline - outlined wide

    # Lookup by name
    _BY_NAME = {
        '5high': '1', 'five_high': '1', '5stroke': '2', 'five_stroke': '2',
        '7high': '3', 'seven_high': '3', '7stroke': '4', 'seven_stroke': '4',
        '7highfancy': '5', 'seven_high_fancy': '5',
        '10high': '6', 'ten_high': '6',
        '7shadow': '7', 'seven_shadow': '7',
        'fhighfancy': '8', 'full_high_fancy': '8',
        'fhigh': '9', 'full_high': '9',
        '7shadowfancy': ':', 'seven_shadow_fancy': ':',
        '5wide': ';', 'five_wide': ';',
        '7wide': '<', 'seven_wide': '<',
        '7widefancy': '=', 'seven_wide_fancy': '=',
        '5widestroke': '>', 'five_wide_stroke': '>'
    }

    @classmethod
    def from_name(cls, name):
        """Get charset code from name string"""
        return cls._BY_NAME.get(name.lower().replace(' ', ''), cls.SEVEN_HIGH)

    @classmethod
    def code(cls, charset_code):
        """Generate character set control sequence: ESC + 0x1A + charset_code"""
        return ESC + '\x1a' + charset_code


# =============================================================================
# Display Positions
# =============================================================================

class Position:
    """Display position codes - control where text appears"""

    TOP_LINE = '"'             # Upper portion of display - headers, titles
    MIDDLE_LINE = ' '          # Center of display (space char) - main content
    BOTTOM_LINE = '&'          # Lower portion of display - status, footers
    FILL = '0'                 # Full display area - maximum visibility
    LEFT = '1'                 # Left-aligned - standard text alignment
    RIGHT = '2'                # Right-aligned - numbers, timestamps

    # Lookup by name
    _BY_NAME = {
        'topline': '"', 'top_line': '"', 'top': '"',
        'midline': ' ', 'middle_line': ' ', 'mid': ' ', 'middle': ' ',
        'botline': '&', 'bottom_line': '&', 'bot': '&', 'bottom': '&',
        'fill': '0', 'left': '1', 'right': '2'
    }

    @classmethod
    def from_name(cls, name):
        """Get position code from name string"""
        return cls._BY_NAME.get(name.lower().replace(' ', ''), cls.FILL)


# =============================================================================
# Speed Codes
# =============================================================================

class Speed:
    """Speed codes for scrolling/animation - ESC + code"""

    SLOWEST = '\x15'           # Speed 1 - deliberate, readable
    SLOW = '\x16'              # Speed 2 - comfortable reading
    MEDIUM = '\x17'            # Speed 3 - standard pace
    FAST = '\x18'              # Speed 4 - quick updates
    FASTEST = '\x19'           # Speed 5 - rapid attention

    # Numeric lookup (1-5)
    _BY_NUMBER = {
        1: '\x15', 2: '\x16', 3: '\x17', 4: '\x18', 5: '\x19'
    }

    @classmethod
    def from_number(cls, num):
        """Get speed code from number (1-5)"""
        return cls._BY_NUMBER.get(num, cls.MEDIUM)

    @classmethod
    def code(cls, speed_code):
        """Generate speed control sequence: ESC + speed_code"""
        return ESC + speed_code


# =============================================================================
# Special Effects (for use with Mode.SPECIAL)
# =============================================================================

class Effect:
    """Special effect codes - used with Mode.SPECIAL"""

    # Atmospheric effects
    TWINKLE = '0'              # Stars twinkling - gentle, pleasant
    SPARKLE = '1'              # Sparkling lights - celebratory, bright
    SNOW = '2'                 # Falling snow - weather, winter theme
    SPRAY = '6'                # Water spray - dynamic, energetic
    STARBURST = '7'            # Explosive star - dramatic, attention-grabbing
    FIREWORKS = 'X'            # Fireworks explosion - celebration

    # Movement effects
    INTERLOCK = '3'            # Interlocking pattern - mechanical
    SWITCH = '4'               # Switching pattern - toggle, alternating
    SLIDE = '5'                # Sliding motion - smooth, directional
    SLOTS = '9'                # Slot machine - random, gaming
    TURBALLOON = 'Y'           # Turbulent balloon - floating, dynamic

    # Themed effects
    WELCOME = '8'              # Welcome message - greeting
    NEWS_FLASH = 'A'           # Breaking news style - urgent
    TRUMPET = 'B'              # Trumpet fanfare - announcement
    CYCLE_COLORS = 'C'         # Rotates through colors - dynamic
    THANK_YOU = 'S'            # Thank you message - gratitude
    NO_SMOKING = 'U'           # No smoking symbol - warning
    NO_DRINK_DRIVE = 'V'       # Don't drink & drive - safety
    FISHIMAL = 'W'             # Fish animation - playful
    BOMB = 'Z'                 # Explosion - extreme urgency

    # Lookup by name
    _BY_NAME = {
        'twinkle': '0', 'sparkle': '1', 'snow': '2', 'interlock': '3',
        'switch': '4', 'slide': '5', 'spray': '6', 'starburst': '7',
        'welcome': '8', 'slots': '9', 'newsflash': 'A', 'news_flash': 'A',
        'trumpet': 'B', 'cyclecolors': 'C', 'cycle_colors': 'C',
        'thankyou': 'S', 'thank_you': 'S', 'nosmoke': 'U', 'no_smoking': 'U',
        'nodrive': 'V', 'no_drink_drive': 'V', 'fishimal': 'W',
        'fireworks': 'X', 'turballoon': 'Y', 'bomb': 'Z'
    }

    @classmethod
    def from_name(cls, name):
        """Get effect code from name string"""
        return cls._BY_NAME.get(name.lower().replace(' ', ''), None)


# =============================================================================
# BetaBrite Class - Main Controller
# =============================================================================

class BetaBrite:
    """
    BetaBrite LED Sign Controller

    Provides methods to communicate with BetaBrite signs using the Alpha Protocol.

    Usage:
        from machine import UART
        uart = UART(2, baudrate=9600, tx=17, rx=16)
        sign = BetaBrite(uart)
        sign.write_text("Hello World!")
        sign.write_priority("URGENT!", mode='flash', color='red')
    """

    def __init__(self, serial, address=DEFAULT_ADDRESS):
        """
        Initialize BetaBrite controller

        Args:
            serial: Serial/UART object for communication
            address: Sign address (default 'Z' for broadcast)
        """
        self.serial = serial
        self.address = address
        self._current_file = FileLabel.FILE_A

    # -------------------------------------------------------------------------
    # Low-Level Protocol Methods
    # -------------------------------------------------------------------------

    def _build_packet(self, command_type, command_data):
        """
        Build a complete Alpha Protocol packet

        Args:
            command_type: Command type code (e.g., 'A' for write text)
            command_data: Command-specific data

        Returns:
            Complete packet as bytes
        """
        # Build packet structure
        packet = (
            NUL * 5 +                    # Sync bytes
            SOH +                        # Start of header
            self.address +               # Sign address
            TYPE_CODE +                  # Sign type code
            command_type +               # Command type
            command_data +               # Command data
            EOT                          # End of transmission
        )
        return packet.encode('latin-1')

    def _build_text_packet(self, file_label, text, mode, position,
                           color=None, charset=None, speed=None, effect=None):
        """
        Build a text write packet with formatting controls

        Args:
            file_label: File label to write to (A-Z or '0' for priority)
            text: Text message to display
            mode: Display mode code
            position: Position code
            color: Optional color code
            charset: Optional character set code
            speed: Optional speed code
            effect: Optional special effect code

        Returns:
            Complete packet as bytes
        """
        # Build control codes sequence
        control_codes = ''

        # Position and mode (always required)
        control_codes += ESC + position + mode

        # Optional: Speed (must come before other formatting)
        if speed:
            control_codes += ESC + speed

        # Optional: Character set
        if charset:
            control_codes += ESC + '\x1a' + charset

        # Optional: Color
        if color:
            control_codes += ESC + color

        # Optional: Special effect (used with Mode.SPECIAL)
        if effect and mode == Mode.SPECIAL:
            control_codes += ESC + 'n' + effect

        # Build command data
        command_data = (
            STX +                        # Start of text
            file_label +                 # File label
            control_codes +              # Control codes
            text +                       # Actual message
            ETX                          # End of text
        )

        return self._build_packet(CommandType.WRITE_TEXT, command_data)

    def _send(self, packet):
        """
        Send packet to sign

        Args:
            packet: Bytes to send
        """
        self.serial.write(packet)

    # -------------------------------------------------------------------------
    # High-Level Display Methods
    # -------------------------------------------------------------------------

    def write_text(self, text, file_label=None, mode='hold', position='fill',
                   color='green', charset='7high', speed=2, effect=None):
        """
        Write text to a file label on the sign

        Args:
            text: Message to display
            file_label: File label (A-Z), defaults to auto-assigned
            mode: Display mode name or code
            position: Position name or code
            color: Color name or code
            charset: Character set name or code
            speed: Speed level (1-5) or code
            effect: Special effect name or code (only with mode='special')

        Example:
            sign.write_text("Hello!", mode='hold', color='green')
            sign.write_text("Warning!", mode='flash', color='red', charset='10high')
        """
        # Use provided file label or default
        if file_label is None:
            file_label = self._current_file

        # Convert names to codes if needed
        mode_code = Mode.from_name(mode) if len(mode) > 1 else mode
        position_code = Position.from_name(position) if len(position) > 1 else position
        color_code = Color.from_name(color) if len(color) > 1 else color
        charset_code = CharSet.from_name(charset) if len(charset) > 1 else charset

        # Handle speed (number or code)
        if isinstance(speed, int):
            speed_code = Speed.from_number(speed)
        else:
            speed_code = speed

        # Handle effect
        effect_code = None
        if effect:
            effect_code = Effect.from_name(effect) if len(effect) > 1 else effect

        # Build and send packet
        packet = self._build_text_packet(
            file_label, text, mode_code, position_code,
            color_code, charset_code, speed_code, effect_code
        )
        self._send(packet)

    def write_priority(self, text, mode='flash', position='fill',
                       color='red', charset='10high', speed=4, effect=None):
        """
        Write priority message (interrupts normal rotation)

        Priority messages display immediately and override the normal
        file rotation sequence until canceled.

        Args:
            text: Priority message to display
            mode: Display mode (default: flash)
            position: Position (default: fill)
            color: Color (default: red)
            charset: Character set (default: 10high for visibility)
            speed: Speed level (default: 4 for attention)
            effect: Optional special effect

        Example:
            sign.write_priority("EMERGENCY!", color='red')
            sign.write_priority("System Ready", mode='hold', color='green')
        """
        self.write_text(
            text,
            file_label=FileLabel.PRIORITY,
            mode=mode,
            position=position,
            color=color,
            charset=charset,
            speed=speed,
            effect=effect
        )

    def cancel_priority(self):
        """
        Cancel priority message and return to normal rotation

        Clears the priority display file, allowing normal file rotation
        to resume.
        """
        # Write empty text to priority file
        packet = self._build_text_packet(
            FileLabel.PRIORITY, '', Mode.HOLD, Position.FILL
        )
        self._send(packet)

    def clear_display(self):
        """
        Clear the display (show blank)

        Writes empty text to the current file label.
        """
        self.write_text('', mode='hold', color='green')

    # -------------------------------------------------------------------------
    # Special Function Methods
    # -------------------------------------------------------------------------

    def set_run_sequence(self, sequence):
        """
        Set the file run sequence for rotation

        Args:
            sequence: String of file labels to rotate through (e.g., 'ABC')

        Example:
            sign.set_run_sequence('ABCD')  # Rotate through files A, B, C, D
            sign.set_run_sequence('A')     # Only show file A
        """
        command_data = (
            STX +
            SpecialFunction.SET_RUN_SEQUENCE +
            sequence +
            ETX
        )
        packet = self._build_packet(CommandType.WRITE_SPECIAL, command_data)
        self._send(packet)

    def soft_reset(self):
        """
        Perform soft reset of the sign

        Resets the sign without clearing memory.
        """
        command_data = (
            STX +
            SpecialFunction.SOFT_RESET +
            ETX
        )
        packet = self._build_packet(CommandType.WRITE_SPECIAL, command_data)
        self._send(packet)

    def clear_memory(self):
        """
        Clear all sign memory

        Warning: This erases all stored text files and configurations.
        """
        command_data = (
            STX +
            SpecialFunction.CLEAR_MEMORY +
            ETX
        )
        packet = self._build_packet(CommandType.WRITE_SPECIAL, command_data)
        self._send(packet)

    def set_time(self, hour, minute):
        """
        Set the sign's internal clock time

        Args:
            hour: Hour (0-23)
            minute: Minute (0-59)
        """
        time_str = f"{hour:02d}{minute:02d}"
        command_data = (
            STX +
            SpecialFunction.SET_TIME +
            time_str +
            ETX
        )
        packet = self._build_packet(CommandType.WRITE_SPECIAL, command_data)
        self._send(packet)

    def set_date(self, month, day, year):
        """
        Set the sign's internal calendar date

        Args:
            month: Month (1-12)
            day: Day (1-31)
            year: Year (2-digit, e.g., 25 for 2025)
        """
        date_str = f"{month:02d}{day:02d}{year:02d}"
        command_data = (
            STX +
            SpecialFunction.SET_DATE +
            date_str +
            ETX
        )
        packet = self._build_packet(CommandType.WRITE_SPECIAL, command_data)
        self._send(packet)

    # -------------------------------------------------------------------------
    # Convenience Methods for Common Displays
    # -------------------------------------------------------------------------

    def show_message(self, text, style='normal'):
        """
        Display message with predefined style

        Args:
            text: Message to display
            style: One of 'normal', 'success', 'warning', 'error', 'info'

        Example:
            sign.show_message("System Ready", style='success')
            sign.show_message("Check Timer!", style='warning')
        """
        styles = {
            'normal': {'mode': 'hold', 'color': 'green', 'charset': '7high'},
            'success': {'mode': 'hold', 'color': 'green', 'charset': '10high'},
            'warning': {'mode': 'flash', 'color': 'amber', 'charset': '10high'},
            'error': {'mode': 'flash', 'color': 'red', 'charset': '10high'},
            'info': {'mode': 'scroll', 'color': 'yellow', 'charset': '7high'},
        }
        config = styles.get(style, styles['normal'])
        self.write_text(text, **config)

    def show_scrolling(self, text, color='rainbow1', speed=2):
        """
        Display scrolling text

        Args:
            text: Message to scroll
            color: Color (default rainbow for visibility)
            speed: Scroll speed 1-5
        """
        self.write_text(text, mode='scroll', color=color, speed=speed)

    def show_alert(self, text, level='warning'):
        """
        Display alert message with appropriate styling

        Args:
            text: Alert message
            level: 'info', 'warning', 'critical'
        """
        levels = {
            'info': {'color': 'yellow', 'mode': 'hold'},
            'warning': {'color': 'amber', 'mode': 'flash'},
            'critical': {'color': 'red', 'mode': 'flash', 'charset': '10high'},
        }
        config = levels.get(level, levels['warning'])
        self.write_text(text, **config)


# =============================================================================
# Display Config Helper - Parse JSON config to method arguments
# =============================================================================

def parse_display_config(config):
    """
    Parse display_config dict from JSON message into method arguments

    Args:
        config: Dict with display configuration (from MQTT message)

    Returns:
        Dict of keyword arguments for write_text/write_priority

    Expected config keys (all optional):
        - mode / mode_code: Display mode
        - color / color_code: Text color
        - charset / charset_code / character_set: Character set
        - position / position_code: Display position
        - speed / speed_code: Animation speed
        - effect / effect_code / special_effect: Special effect
    """
    args = {}

    # Mode - prefer code, fall back to name
    if 'mode_code' in config:
        args['mode'] = config['mode_code']
    elif 'mode' in config:
        args['mode'] = config['mode']

    # Color - prefer code, fall back to name
    if 'color_code' in config:
        args['color'] = config['color_code']
    elif 'color' in config:
        args['color'] = config['color']

    # Character set - multiple possible key names
    for key in ['charset_code', 'charset', 'character_set']:
        if key in config:
            args['charset'] = config[key]
            break

    # Position - prefer code, fall back to name
    if 'position_code' in config:
        args['position'] = config['position_code']
    elif 'position' in config:
        args['position'] = config['position']

    # Speed - handle both numeric and code formats
    if 'speed_code' in config:
        # Speed code is like '\027' - extract the character
        speed_str = config['speed_code']
        if speed_str.startswith('\\'):
            try:
                # Parse octal escape like '\027'
                args['speed'] = chr(int(speed_str[1:], 8))
            except (ValueError, IndexError):
                pass
        else:
            args['speed'] = speed_str
    elif 'speed' in config:
        args['speed'] = config['speed']

    # Effect - prefer code, fall back to name
    if 'effect_code' in config:
        args['effect'] = config['effect_code']
    elif 'special_effect' in config:
        args['effect'] = config['special_effect']
    elif 'effect' in config:
        args['effect'] = config['effect']

    return args
