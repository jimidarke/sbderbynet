"""
Unit Tests for BetaBrite Library

Tests the Alpha Protocol implementation, display modes, colors,
character sets, and command generation.
"""

import pytest
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from betabrite import (
    BetaBrite, Mode, Color, CharSet, Position, Speed, Effect,
    FileLabel, CommandType, SpecialFunction,
    NUL, SOH, STX, ETX, EOT, ESC,
    parse_display_config
)


class TestControlCharacters:
    """Test control character constants"""

    def test_nul_value(self):
        assert NUL == '\x00'

    def test_soh_value(self):
        assert SOH == '\x01'

    def test_stx_value(self):
        assert STX == '\x02'

    def test_etx_value(self):
        assert ETX == '\x03'

    def test_eot_value(self):
        assert EOT == '\x04'

    def test_esc_value(self):
        assert ESC == '\x1b'


class TestModeClass:
    """Test Mode constants and lookup"""

    def test_basic_modes(self):
        assert Mode.ROTATE == 'a'
        assert Mode.HOLD == 'b'
        assert Mode.FLASH == 'c'
        assert Mode.SCROLL == 'm'
        assert Mode.AUTO == 'o'

    def test_roll_modes(self):
        assert Mode.ROLL_UP == 'e'
        assert Mode.ROLL_DOWN == 'f'
        assert Mode.ROLL_LEFT == 'g'
        assert Mode.ROLL_RIGHT == 'h'
        assert Mode.ROLL_IN == 'p'
        assert Mode.ROLL_OUT == 'q'

    def test_wipe_modes(self):
        assert Mode.WIPE_UP == 'i'
        assert Mode.WIPE_DOWN == 'j'
        assert Mode.WIPE_LEFT == 'k'
        assert Mode.WIPE_RIGHT == 'l'
        assert Mode.WIPE_IN == 'r'
        assert Mode.WIPE_OUT == 's'

    def test_advanced_modes(self):
        assert Mode.EXPLODE == 'u'
        assert Mode.SPECIAL == 'n'

    def test_from_name_basic(self):
        assert Mode.from_name('hold') == 'b'
        assert Mode.from_name('flash') == 'c'
        assert Mode.from_name('scroll') == 'm'

    def test_from_name_case_insensitive(self):
        assert Mode.from_name('HOLD') == 'b'
        assert Mode.from_name('Flash') == 'c'
        assert Mode.from_name('SCROLL') == 'm'

    def test_from_name_with_underscore(self):
        assert Mode.from_name('roll_up') == 'e'
        assert Mode.from_name('roll_left') == 'g'
        assert Mode.from_name('wipe_in') == 'r'

    def test_from_name_without_underscore(self):
        assert Mode.from_name('rollup') == 'e'
        assert Mode.from_name('rollleft') == 'g'
        assert Mode.from_name('wipein') == 'r'

    def test_from_name_unknown_returns_hold(self):
        assert Mode.from_name('unknown') == Mode.HOLD
        assert Mode.from_name('invalid') == Mode.HOLD


class TestColorClass:
    """Test Color constants and lookup"""

    def test_standard_colors(self):
        assert Color.RED == '1'
        assert Color.GREEN == '2'
        assert Color.AMBER == '3'
        assert Color.YELLOW == '8'
        assert Color.ORANGE == '7'

    def test_dimmed_colors(self):
        assert Color.DIM_RED == '4'
        assert Color.DIM_GREEN == '5'
        assert Color.BROWN == '6'

    def test_dynamic_colors(self):
        assert Color.RAINBOW_1 == '9'
        assert Color.RAINBOW_2 == 'A'
        assert Color.COLOR_MIX == 'B'
        assert Color.AUTO == 'C'

    def test_from_name(self):
        assert Color.from_name('red') == '1'
        assert Color.from_name('green') == '2'
        assert Color.from_name('amber') == '3'

    def test_from_name_case_insensitive(self):
        assert Color.from_name('RED') == '1'
        assert Color.from_name('Green') == '2'

    def test_from_name_with_underscore(self):
        assert Color.from_name('dim_red') == '4'
        assert Color.from_name('rainbow_1') == '9'

    def test_from_name_without_underscore(self):
        assert Color.from_name('dimred') == '4'
        assert Color.from_name('rainbow1') == '9'

    def test_from_name_unknown_returns_green(self):
        assert Color.from_name('unknown') == Color.GREEN

    def test_color_code_escape_sequence(self):
        code = Color.code('1')
        assert code == ESC + '1'


class TestCharSetClass:
    """Test CharSet constants and lookup"""

    def test_standard_heights(self):
        assert CharSet.FIVE_HIGH == '1'
        assert CharSet.SEVEN_HIGH == '3'
        assert CharSet.TEN_HIGH == '6'

    def test_stroke_fonts(self):
        assert CharSet.FIVE_STROKE == '2'
        assert CharSet.SEVEN_STROKE == '4'

    def test_fancy_fonts(self):
        assert CharSet.SEVEN_HIGH_FANCY == '5'
        assert CharSet.FULL_HIGH_FANCY == '8'

    def test_from_name(self):
        assert CharSet.from_name('5high') == '1'
        assert CharSet.from_name('7high') == '3'
        assert CharSet.from_name('10high') == '6'

    def test_from_name_case_insensitive(self):
        assert CharSet.from_name('7HIGH') == '3'
        assert CharSet.from_name('10High') == '6'

    def test_from_name_with_underscore(self):
        assert CharSet.from_name('seven_high') == '3'
        assert CharSet.from_name('ten_high') == '6'

    def test_from_name_unknown_returns_seven_high(self):
        assert CharSet.from_name('unknown') == CharSet.SEVEN_HIGH

    def test_charset_code_escape_sequence(self):
        code = CharSet.code('3')
        assert code == ESC + '\x1a' + '3'


class TestPositionClass:
    """Test Position constants and lookup"""

    def test_positions(self):
        assert Position.TOP_LINE == '"'
        assert Position.MIDDLE_LINE == ' '
        assert Position.BOTTOM_LINE == '&'
        assert Position.FILL == '0'
        assert Position.LEFT == '1'
        assert Position.RIGHT == '2'

    def test_from_name(self):
        assert Position.from_name('fill') == '0'
        assert Position.from_name('top') == '"'
        assert Position.from_name('middle') == ' '
        assert Position.from_name('bottom') == '&'

    def test_from_name_aliases(self):
        assert Position.from_name('topline') == '"'
        assert Position.from_name('midline') == ' '
        assert Position.from_name('botline') == '&'

    def test_from_name_unknown_returns_fill(self):
        assert Position.from_name('unknown') == Position.FILL


class TestSpeedClass:
    """Test Speed constants and lookup"""

    def test_speed_values(self):
        assert Speed.SLOWEST == '\x15'
        assert Speed.SLOW == '\x16'
        assert Speed.MEDIUM == '\x17'
        assert Speed.FAST == '\x18'
        assert Speed.FASTEST == '\x19'

    def test_from_number(self):
        assert Speed.from_number(1) == '\x15'
        assert Speed.from_number(2) == '\x16'
        assert Speed.from_number(3) == '\x17'
        assert Speed.from_number(4) == '\x18'
        assert Speed.from_number(5) == '\x19'

    def test_from_number_invalid_returns_medium(self):
        assert Speed.from_number(0) == Speed.MEDIUM
        assert Speed.from_number(6) == Speed.MEDIUM
        assert Speed.from_number(99) == Speed.MEDIUM

    def test_speed_code_escape_sequence(self):
        code = Speed.code('\x17')
        assert code == ESC + '\x17'


class TestEffectClass:
    """Test Effect constants and lookup"""

    def test_atmospheric_effects(self):
        assert Effect.TWINKLE == '0'
        assert Effect.SPARKLE == '1'
        assert Effect.SNOW == '2'
        assert Effect.STARBURST == '7'

    def test_movement_effects(self):
        assert Effect.INTERLOCK == '3'
        assert Effect.SWITCH == '4'
        assert Effect.SLIDE == '5'
        assert Effect.SLOTS == '9'

    def test_themed_effects(self):
        assert Effect.WELCOME == '8'
        assert Effect.NEWS_FLASH == 'A'
        assert Effect.BOMB == 'Z'
        assert Effect.FIREWORKS == 'X'

    def test_from_name(self):
        assert Effect.from_name('twinkle') == '0'
        assert Effect.from_name('sparkle') == '1'
        assert Effect.from_name('bomb') == 'Z'

    def test_from_name_with_underscore(self):
        assert Effect.from_name('news_flash') == 'A'
        assert Effect.from_name('cycle_colors') == 'C'

    def test_from_name_unknown_returns_none(self):
        assert Effect.from_name('unknown') is None


class TestBetaBriteInit:
    """Test BetaBrite initialization"""

    def test_init_with_default_address(self, mock_uart):
        sign = BetaBrite(mock_uart)
        assert sign.serial == mock_uart
        assert sign.address == 'Z'

    def test_init_with_custom_address(self, mock_uart):
        sign = BetaBrite(mock_uart, address='1')
        assert sign.address == '1'


class TestBetaBritePacketBuilding:
    """Test packet building functionality"""

    def test_packet_starts_with_sync_bytes(self, betabrite, mock_uart):
        betabrite.write_text("Test")
        data = mock_uart.get_last_write()
        # Should start with 5 NUL bytes
        assert data[:5] == b'\x00\x00\x00\x00\x00'

    def test_packet_has_soh_after_sync(self, betabrite, mock_uart):
        betabrite.write_text("Test")
        data = mock_uart.get_last_write()
        assert data[5:6] == b'\x01'  # SOH

    def test_packet_has_address(self, betabrite, mock_uart):
        betabrite.write_text("Test")
        data = mock_uart.get_last_write()
        assert data[6:7] == b'Z'  # Default address

    def test_packet_has_type_code(self, betabrite, mock_uart):
        betabrite.write_text("Test")
        data = mock_uart.get_last_write()
        assert data[7:9] == b'00'  # Type code

    def test_packet_has_command_type(self, betabrite, mock_uart):
        betabrite.write_text("Test")
        data = mock_uart.get_last_write()
        assert data[9:10] == b'A'  # Write text command

    def test_packet_contains_message(self, betabrite, mock_uart):
        betabrite.write_text("Hello")
        data = mock_uart.get_last_write()
        assert b'Hello' in data

    def test_packet_ends_with_eot(self, betabrite, mock_uart):
        betabrite.write_text("Test")
        data = mock_uart.get_last_write()
        assert data[-1:] == b'\x04'  # EOT


class TestBetaBriteWriteText:
    """Test write_text method"""

    def test_write_text_basic(self, betabrite, mock_uart):
        betabrite.write_text("Hello World!")
        assert len(mock_uart.written_data) == 1
        assert b'Hello World!' in mock_uart.get_last_write()

    def test_write_text_with_mode_name(self, betabrite, mock_uart):
        betabrite.write_text("Test", mode='flash')
        data = mock_uart.get_last_write()
        # Mode code 'c' should be in the control sequence
        assert b'c' in data

    def test_write_text_with_mode_code(self, betabrite, mock_uart):
        betabrite.write_text("Test", mode='b')  # Direct code
        data = mock_uart.get_last_write()
        assert b'b' in data

    def test_write_text_with_color_name(self, betabrite, mock_uart):
        betabrite.write_text("Test", color='red')
        data = mock_uart.get_last_write()
        # Color code should follow ESC
        assert b'\x1b1' in data

    def test_write_text_with_charset_name(self, betabrite, mock_uart):
        betabrite.write_text("Test", charset='10high')
        data = mock_uart.get_last_write()
        # Charset code should follow ESC + 0x1A
        assert b'\x1b\x1a6' in data

    def test_write_text_with_speed_number(self, betabrite, mock_uart):
        betabrite.write_text("Test", speed=4)
        data = mock_uart.get_last_write()
        # Speed code for 4 is \x18
        assert b'\x1b\x18' in data

    def test_write_text_to_specific_file(self, betabrite, mock_uart):
        betabrite.write_text("Test", file_label='B')
        data = mock_uart.get_last_write()
        # File label should be after STX
        assert b'\x02B' in data


class TestBetaBritePriority:
    """Test priority message handling"""

    def test_write_priority_uses_file_label_zero(self, betabrite, mock_uart):
        betabrite.write_priority("URGENT!")
        data = mock_uart.get_last_write()
        # Priority file label is '0'
        assert b'\x020' in data

    def test_write_priority_default_color_red(self, betabrite, mock_uart):
        betabrite.write_priority("URGENT!")
        data = mock_uart.get_last_write()
        assert b'\x1b1' in data  # Red color code

    def test_write_priority_default_mode_flash(self, betabrite, mock_uart):
        betabrite.write_priority("URGENT!")
        data = mock_uart.get_last_write()
        assert b'c' in data  # Flash mode

    def test_cancel_priority_writes_empty_to_priority_file(self, betabrite, mock_uart):
        betabrite.cancel_priority()
        data = mock_uart.get_last_write()
        assert b'\x020' in data  # Priority file label


class TestBetaBriteSpecialFunctions:
    """Test special function commands"""

    def test_set_run_sequence(self, betabrite, mock_uart):
        betabrite.set_run_sequence('ABC')
        data = mock_uart.get_last_write()
        assert b'E' in data  # Special function command type
        assert b'ABC' in data

    def test_soft_reset(self, betabrite, mock_uart):
        betabrite.soft_reset()
        data = mock_uart.get_last_write()
        assert b'E' in data  # Special function command type

    def test_clear_memory(self, betabrite, mock_uart):
        betabrite.clear_memory()
        data = mock_uart.get_last_write()
        assert b'E' in data


class TestBetaBriteConvenienceMethods:
    """Test convenience methods"""

    def test_show_message_normal(self, betabrite, mock_uart):
        betabrite.show_message("Test", style='normal')
        data = mock_uart.get_last_write()
        assert b'Test' in data
        assert b'\x1b2' in data  # Green color

    def test_show_message_success(self, betabrite, mock_uart):
        betabrite.show_message("Success!", style='success')
        data = mock_uart.get_last_write()
        assert b'Success!' in data
        assert b'\x1b2' in data  # Green

    def test_show_message_warning(self, betabrite, mock_uart):
        betabrite.show_message("Warning!", style='warning')
        data = mock_uart.get_last_write()
        assert b'Warning!' in data
        assert b'\x1b3' in data  # Amber

    def test_show_message_error(self, betabrite, mock_uart):
        betabrite.show_message("Error!", style='error')
        data = mock_uart.get_last_write()
        assert b'Error!' in data
        assert b'\x1b1' in data  # Red

    def test_show_scrolling(self, betabrite, mock_uart):
        betabrite.show_scrolling("Scrolling text")
        data = mock_uart.get_last_write()
        assert b'Scrolling text' in data
        assert b'm' in data  # Scroll mode

    def test_show_alert_warning(self, betabrite, mock_uart):
        betabrite.show_alert("Alert!", level='warning')
        data = mock_uart.get_last_write()
        assert b'Alert!' in data
        assert b'\x1b3' in data  # Amber

    def test_show_alert_critical(self, betabrite, mock_uart):
        betabrite.show_alert("Critical!", level='critical')
        data = mock_uart.get_last_write()
        assert b'Critical!' in data
        assert b'\x1b1' in data  # Red


class TestDisplayConfigParsing:
    """Test parse_display_config function"""

    def test_parse_mode_code(self):
        config = {'mode_code': 'c'}
        args = parse_display_config(config)
        assert args['mode'] == 'c'

    def test_parse_mode_name(self):
        config = {'mode': 'flash'}
        args = parse_display_config(config)
        assert args['mode'] == 'flash'

    def test_mode_code_takes_precedence(self):
        config = {'mode': 'hold', 'mode_code': 'c'}
        args = parse_display_config(config)
        assert args['mode'] == 'c'

    def test_parse_color_code(self):
        config = {'color_code': '1'}
        args = parse_display_config(config)
        assert args['color'] == '1'

    def test_parse_color_name(self):
        config = {'color': 'red'}
        args = parse_display_config(config)
        assert args['color'] == 'red'

    def test_parse_charset_code(self):
        config = {'charset_code': '6'}
        args = parse_display_config(config)
        assert args['charset'] == '6'

    def test_parse_charset_name(self):
        config = {'character_set': '10high'}
        args = parse_display_config(config)
        assert args['charset'] == '10high'

    def test_parse_position_code(self):
        config = {'position_code': '0'}
        args = parse_display_config(config)
        assert args['position'] == '0'

    def test_parse_speed_numeric(self):
        config = {'speed': 4}
        args = parse_display_config(config)
        assert args['speed'] == 4

    def test_parse_effect_code(self):
        config = {'effect_code': 'Z'}
        args = parse_display_config(config)
        assert args['effect'] == 'Z'

    def test_parse_effect_name(self):
        config = {'special_effect': 'bomb'}
        args = parse_display_config(config)
        assert args['effect'] == 'bomb'

    def test_parse_empty_config(self):
        config = {}
        args = parse_display_config(config)
        assert args == {}

    def test_parse_full_config(self, sample_display_config):
        args = parse_display_config(sample_display_config)
        assert 'mode' in args
        assert 'color' in args
        assert 'charset' in args
        assert 'position' in args
