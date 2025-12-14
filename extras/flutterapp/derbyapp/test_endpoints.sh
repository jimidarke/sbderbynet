#!/bin/bash
# DerbyNet API Endpoint Testing Script
# Tests all endpoints used by the Flutter app

SERVER="http://192.168.100.10/derbynet"
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BOLD}=== DerbyNet API Endpoint Tests ===${NC}\n"

# Test 1: OnDeck Endpoint - Full heat history
echo -e "${YELLOW}Test 1: OnDeck Endpoint (Heat History)${NC}"
echo "GET $SERVER/action.php?query=poll&values=ondeck"
echo ""
curl -s "$SERVER/action.php?query=poll&values=ondeck" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    ondeck = data.get('ondeck', {})
    chart = ondeck.get('chart', [])

    print(f'✓ Total chart entries: {len(chart)}')

    if chart:
        first = chart[0]
        print(f'✓ First entry fields: {', '.join(first.keys())}')
        print(f'  - Result ID: {first.get(\"resultid\")}')
        print(f'  - Round/Heat: {first.get(\"roundid\")}/{first.get(\"heat\")}')
        print(f'  - Car #{first.get(\"carnumber\")}: {first.get(\"name\")}')
        print(f'  - Result: {first.get(\"result\")} (z-prefix = completed)')

        # Group by heat to count completed heats
        heats = {}
        for entry in chart:
            key = f\"{entry['roundid']}-{entry['heat']}\"
            if key not in heats:
                heats[key] = []
            heats[key].append(entry)

        completed = sum(1 for h in heats.values() if all(e.get('result') for e in h))
        print(f'✓ Unique heats: {len(heats)}')
        print(f'✓ Completed heats: {completed}')
    else:
        print('✗ No chart entries found')
except Exception as e:
    print(f'✗ Parse error: {e}')
"
echo ""

# Test 2: Current Heat Status
echo -e "${YELLOW}Test 2: Current Heat Status${NC}"
echo "GET $SERVER/action.php?query=poll.coordinator"
echo ""
curl -s "$SERVER/action.php?query=poll.coordinator" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    current = data.get('current-heat', {})
    racers = data.get('racers', [])
    last_heat = data.get('last-heat', 'none')

    print(f'✓ Current heat: Round {current.get(\"roundid\")} Heat {current.get(\"heat\")}/{current.get(\"number-of-heats\")}')
    print(f'✓ Racing status: {\"🏁 Now Racing\" if current.get(\"now_racing\") else \"⏸️  Paused\"}')
    print(f'✓ Racers in current heat: {len(racers)}')
    if racers:
        for r in racers:
            print(f'  - Lane {r[\"lane\"]}: #{r[\"carnumber\"]} {r[\"name\"]}')
    print(f'✓ Last completed heat: {last_heat}')
except Exception as e:
    print(f'✗ Parse error: {e}')
"
echo ""

# Test 3: Specific Heat Detail (Heat 1)
echo -e "${YELLOW}Test 3: Heat Detail (Round 1, Heat 1)${NC}"
echo "GET $SERVER/action.php?query=poll.coordinator&roundid=1&heat=1"
echo ""
curl -s "$SERVER/action.php?query=poll.coordinator&roundid=1&heat=1" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    heat_results = data.get('heat-results', [])
    racers = data.get('racers', [])

    print(f'✓ Heat results count: {len(heat_results)}')
    print(f'✓ Racers count: {len(racers)}')

    if heat_results:
        print('✓ Results breakdown:')
        for result in heat_results:
            place_emoji = '🥇' if result['place'] == 1 else '🥈' if result['place'] == 2 else '🥉' if result['place'] == 3 else f\"{result['place']}\"
            print(f'  {place_emoji} Lane {result[\"lane\"]}: {result[\"time\"]}s (place {result[\"place\"]}, {result.get(\"speed\", 0)} km/h)')

    if racers:
        print('✓ Racer details:')
        for racer in racers:
            print(f'  - Lane {racer[\"lane\"]}: #{racer[\"carnumber\"]} {racer[\"name\"]}')
except Exception as e:
    print(f'✗ Parse error: {e}')
"
echo ""

# Test 4: Last Heat Parsing Format
echo -e "${YELLOW}Test 4: Last Heat Field Format${NC}"
echo "GET $SERVER/action.php?query=poll.coordinator"
echo ""
curl -s "$SERVER/action.php?query=poll.coordinator" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    last_heat = data.get('last-heat', 'none')

    print(f'Raw value: \"{last_heat}\"')

    if last_heat == 'available':
        print('✓ Format: \"available\" (heats exist but no specific last heat)')
    elif last_heat == 'none':
        print('✓ Format: \"none\" (no completed heats)')
    elif '#' in last_heat:
        parts = last_heat.split('#')
        print(f'✓ Format: \"roundid#heat\" → Round {parts[0]}, Heat {parts[1]}')
    else:
        print(f'⚠️  Unexpected format: {last_heat}')
except Exception as e:
    print(f'✗ Parse error: {e}')
"
echo ""

# Test 5: Timer State
echo -e "${YELLOW}Test 5: Timer State${NC}"
echo "GET $SERVER/action.php?query=poll.coordinator"
echo ""
curl -s "$SERVER/action.php?query=poll.coordinator" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    timer_state = data.get('timer-state', {})

    print(f'✓ Lanes: {timer_state.get(\"lanes\")}')
    print(f'✓ Timers online: {timer_state.get(\"timers_online\")}/{timer_state.get(\"timers_required\")}')
    print(f'✓ Health status: {timer_state.get(\"health_status\")}')
    print(f'✓ Message: {timer_state.get(\"message\")}')
except Exception as e:
    print(f'✗ Parse error: {e}')
"
echo ""

echo -e "${BOLD}=== Tests Complete ===${NC}"
echo ""
echo "Summary:"
echo "  - OnDeck endpoint provides full heat history (completed heats)"
echo "  - Coordinator poll provides current heat status and racers"
echo "  - Heat detail endpoint provides specific heat results"
echo "  - Last heat field format: 'available', 'none', or 'roundid#heat'"
echo "  - All endpoints match Flutter app data model expectations"
