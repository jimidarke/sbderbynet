"""
LED Sign Content Generator for DerbyNet Race Server

Generates JSON message dicts for BetaBrite LED signs based on race state.
Messages match the DerbyNet LED sign firmware format (extras/ledsign/src/main.py).

The firmware's parse_display_config() accepts both raw Alpha Protocol codes
and human-readable names. We use names for clarity.

Version: 0.1.0
"""

# Race state constants (must match derbyRace.py)
RACE_STATE_UNCONFIGURED = "UNCONFIGURED"
RACE_STATE_STOPPED = "STOPPED"
RACE_STATE_STAGING = "STAGING"
RACE_STATE_RACING = "RACING"
RACE_STATE_FINISHED = "FINISHED"


def _format_message(message, mode='hold', color='green', charset='10high',
                    position='fill', priority=False, duration=15):
    """Build a JSON message dict matching the firmware's expected format.

    The firmware (extras/ledsign/src/main.py handle_display_message) reads:
      - message: text to display
      - display_config.priority: if True, uses write_priority (interrupts rotation)
      - display_config.duration: seconds before priority auto-expires
      - display_config.mode/color/charset/position: passed to parse_display_config()
    """
    return {
        "message": message,
        "display_config": {
            "mode": mode,
            "color": color,
            "charset": charset,
            "position": position,
            "priority": priority,
            "duration": duration,
        }
    }


def lane_sign_message(pinny, race_state, next_pinny=None):
    """Generate display content for a usher-lane sign.

    Args:
        pinny: Current racer's pinny number (string, e.g. "0042")
        race_state: Current race state constant
        next_pinny: Next heat's racer pinny (optional)

    Returns:
        dict: JSON message for the LED sign firmware
    """
    if race_state in (RACE_STATE_STAGING, RACE_STATE_RACING):
        text = f"#{pinny}"
        if next_pinny:
            text += f"\rNEXT: #{next_pinny}"  # \r = BetaBrite newline
        return _format_message(
            message=text,
            color='green',
            mode='hold',
            charset='10high',
            duration=60,
        )

    elif race_state == RACE_STATE_FINISHED:
        return _format_message(
            message="DONE",
            color='amber',
            mode='hold',
            duration=5,
        )

    else:  # STOPPED, UNCONFIGURED
        return _format_message(
            message=" ",
            color='green',
            mode='hold',
            duration=60,
        )


def starter_sign_message(race_state):
    """Generate display content for the starter sign.

    Args:
        race_state: Current race state constant

    Returns:
        dict: JSON message for the LED sign firmware
    """
    if race_state == RACE_STATE_STAGING:
        return _format_message(
            message="SET",
            color='amber',
            mode='hold',
            charset='10high',
            duration=60,
        )

    elif race_state == RACE_STATE_RACING:
        return _format_message(
            message="GO!",
            color='green',
            mode='flash',
            charset='10high',
            priority=True,
            duration=5,
        )

    elif race_state == RACE_STATE_FINISHED:
        return _format_message(
            message="FINISHED",
            color='red',
            mode='hold',
            charset='7high',
            duration=15,
        )

    else:  # STOPPED, UNCONFIGURED
        return _format_message(
            message="READY",
            color='amber',
            mode='hold',
            charset='10high',
            duration=60,
        )
