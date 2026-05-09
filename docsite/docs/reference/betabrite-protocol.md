# BetaBrite Protocol

Reference for the BetaBrite Alpha-Protocol features used by the LED-sign firmware (`extras/ledsign/src/betabrite.py`). Display modes, special effects, colours, character sets, and how they map onto race-day uses.

For component-level docs (wiring, deployment, MQTT topics), see [LED Signs](../components/led-signs.md).

---

## Display modes

### Basic

| Mode | Code | Description |
|---|---|---|
| Rotate | `a` | cycles through text files (default continuous display) |
| Hold | `b` | static, no movement |
| Flash | `c` | text blinks on/off (critical alerts) |
| Scroll | `m` | horizontal scroll (long messages) |
| Auto | `o` | sign chooses display method |

### Motion

| Mode | Code | Description |
|---|---|---|
| Roll Up / Down | `e` / `f` | text rolls in vertically |
| Roll Left / Right | `g` / `h` | rolls in horizontally |
| Roll In / Out | `p` / `q` | converging / diverging |

### Wipes

| Mode | Code | Description |
|---|---|---|
| Wipe Up / Down | `i` / `j` | clean vertical reveal |
| Wipe Left / Right | `k` / `l` | clean horizontal reveal |
| Wipe In / Out | `r` / `s` | converging / diverging reveal |

### Advanced

| Mode | Code | Description |
|---|---|---|
| Compressed Rotate | `t` | compact rotation |
| Explode | `u` | text explodes outward |
| Clock | `v` | time / date display |
| Special | `n` | enables special effects |

---

## Special effects (use with mode `n`)

### Atmospheric

| Effect | Code |
|---|---|
| Twinkle | `0` |
| Sparkle | `1` |
| Snow | `2` |
| Spray | `6` |
| Starburst | `7` |
| Fireworks | `X` |

### Movement

| Effect | Code |
|---|---|
| Interlock | `3` |
| Switch | `4` |
| Slide | `5` |
| Slots | `9` |
| Turballoon | `Y` |

### Themed

| Effect | Code |
|---|---|
| Welcome | `8` |
| News Flash | `A` |
| Trumpet | `B` |
| Thank You | `S` |
| Fishimal | `W` |
| Bomb | `Z` |

### Colour

| Effect | Code |
|---|---|
| Cycle Colors | `C` |

---

## Colours

| Colour | Code |
|---|---|
| Red | `1` |
| Green | `2` |
| Amber | `3` |
| Yellow | `8` |
| Orange | `7` |
| Dim Red | `4` |
| Dim Green | `5` |
| Brown | `6` |
| Rainbow 1 / 2 | `9` / `A` |
| Color Mix | `B` |
| Auto Color | `C` |

---

## Display positions

| Position | Code |
|---|---|
| Top line | `"` |
| Middle line | (space) |
| Bottom line | `&` |
| Fill | `0` |
| Left | `1` |
| Right | `2` |

---

## Character sets

### Standard

| Set | Code |
|---|---|
| 5 High | `1` |
| 5 Stroke | `2` |
| 7 High | `3` |
| 7 Stroke | `4` |
| 7 High Fancy | `5` |
| 10 High | `6` |

### Enhanced

| Set | Code |
|---|---|
| 7 Shadow | `7` |
| Full High Fancy | `8` |
| Full High | `9` |
| 7 Shadow Fancy | `:` |

### Wide

| Set | Code |
|---|---|
| 5 Wide | `;` |
| 7 Wide | `<` |
| 7 Wide Fancy | `=` |
| 5 Wide Stroke | `>` |

---

## Text-formatting controls

| Attribute | Code | Effect |
|---|---|---|
| Wide | `0` | expanded width |
| Double Wide | `1` | very wide |
| Double High | `2` | very tall |
| True Descenders | `3` | better typography |
| Fixed Width | `4` | monospace |
| Fancy | `5` | decorative |
| Shadow | `7` | dimensional |

### Speed

| Speed | Code |
|---|---|
| 1 (slowest) | `\025` |
| 2 | `\026` |
| 3 | `\027` |
| 4 | `\030` |
| 5 (fastest) | `\031` |

### Special formatting

| Control | Code |
|---|---|
| New line | `\015` |
| New page | `\014` |
| Character flash | `\007` |
| No-hold speed | `\011` |

---

## Recommended presets

### Critical alert

```
mode: flash (c)  /  newsflash (A)
effect: starburst (7)  /  bomb (Z)
color: red (1)
speed: 5
charset: 10 High (6)
position: fill (0)
priority: true
```

### Warning

```
mode: scroll (m)  /  special (n)
effect: sparkle (1)  /  trumpet (B)
color: amber (3)  /  orange (7)
speed: 3
charset: 7 High (3)
position: top line (")
```

### Info

```
mode: rotate (a)  /  scroll (m)
effect: twinkle (0)  /  welcome (8)
color: green (2)  /  auto (C)
speed: 2
charset: 7 High (3)
position: middle line ( )
```

### Debug / status

```
mode: hold (b)
color: dim green (5)
speed: 1
charset: 5 High (1)
position: bottom line (&)
```

---

## Display-config payload (sent over MQTT)

The race server publishes JSON like:

```json
{
  "message": "Justin (#17) please report to staging",
  "display_config": {
    "mode": "scroll",
    "special_effect": "trumpet",
    "color": "amber",
    "character_set": "7high",
    "speed": 3,
    "position": "topline",
    "priority": false,
    "duration": 30
  }
}
```

The firmware maps named values to BetaBrite codes via the `betabrite.py` library. See `extras/ledsign/src/main.py` (`processAlertMessage`-style handler) and `extras/ledsign/ESP32_BETABRITE_IMPLEMENTATION.md` for the full mapping table.

---

## Capability matrix

The library exposes 23 display modes × 21 special effects × 12 colours × 14 character sets — many tens of thousands of unique combinations. In practice we use a small set of presets matched to race state (see [LED Signs](../components/led-signs.md) "What each sign shows during a race") and a wider palette for sponsor / audience zones.
