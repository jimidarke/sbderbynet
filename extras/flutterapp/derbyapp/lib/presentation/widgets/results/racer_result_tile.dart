import 'package:flutter/material.dart';
import '../../../data/models/race/racer_model.dart';
import '../../../data/models/race/heat_result_model.dart';

/// Individual racer tile showing racer info and optional result
class RacerResultTile extends StatelessWidget {
  final RacerModel racer;
  final HeatResultModel? result;

  const RacerResultTile({
    super.key,
    required this.racer,
    this.result,
  });

  @override
  Widget build(BuildContext context) {
    final hasResult = result != null;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: hasResult ? Colors.green[50] : Colors.grey[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: hasResult ? Colors.green : Colors.grey[300]!,
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Lane badge
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: _getLaneColor(racer.lane),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '${racer.lane}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),

          // Racer info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  racer.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 2),
                if (racer.carname.isNotEmpty) ...[
                  Text(
                    racer.carname,
                    style: TextStyle(
                      color: Colors.grey[700],
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 2),
                ],
                if (racer.carnumber != null)
                  Text(
                    '#${racer.carnumber}',
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 12,
                    ),
                  ),
              ],
            ),
          ),

          // Result display
          if (hasResult)
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Place badge
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _getPlaceColor(result!.place),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _getPlaceText(result!.place),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                // Time
                Text(
                  '${result!.time.toStringAsFixed(3)}s',
                  style: const TextStyle(
                    fontFamily: 'RobotoMono',
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                // Speed
                if (result!.speed > 0)
                  Text(
                    '${result!.speed} km/h',
                    style: TextStyle(
                      color: Colors.grey[600],
                      fontSize: 11,
                    ),
                  ),
              ],
            )
          else
            Text(
              'Waiting...',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 14,
                fontStyle: FontStyle.italic,
              ),
            ),
        ],
      ),
    );
  }

  Color _getLaneColor(int lane) {
    final colors = [
      Colors.blue,
      Colors.red,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
    ];
    return colors[(lane - 1) % colors.length];
  }

  Color _getPlaceColor(int place) {
    switch (place) {
      case 1:
        return Colors.amber[700]!;
      case 2:
        return Colors.grey[600]!;
      case 3:
        return Colors.brown[400]!;
      default:
        return Colors.blue[600]!;
    }
  }

  String _getPlaceText(int place) {
    switch (place) {
      case 1:
        return '1st';
      case 2:
        return '2nd';
      case 3:
        return '3rd';
      default:
        return '${place}th';
    }
  }
}
