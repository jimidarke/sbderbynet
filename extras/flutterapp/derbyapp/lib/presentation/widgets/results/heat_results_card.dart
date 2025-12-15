import 'package:flutter/material.dart';
import '../../../data/models/race/heat_detail_model.dart';
import '../../../core/theme/app_colors.dart';

/// Reusable card widget displaying heat results with podium visualization
class HeatResultsCard extends StatelessWidget {
  final HeatDetailModel heatDetail;

  const HeatResultsCard({
    super.key,
    required this.heatDetail,
  });

  @override
  Widget build(BuildContext context) {
    if (!heatDetail.isComplete || heatDetail.results.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Text(
              'No results available',
              style: TextStyle(color: Colors.grey[600]),
            ),
          ),
        ),
      );
    }

    final sortedResults = heatDetail.racersWithResults;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.emoji_events, size: 24),
                const SizedBox(width: 8),
                Text(
                  'Race Results',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const Divider(height: 24),

            // Podium visualization (top 3)
            if (sortedResults.length >= 3) ...[
              _buildPodium(context, sortedResults),
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 16),
            ],

            // All results list
            ...sortedResults.asMap().entries.map((entry) {
              return _buildResultRow(
                context,
                entry.value.racer.name,
                entry.value.racer.carnumber ?? 0,
                entry.value.result.place,
                entry.value.result.time,
                entry.value.result.speed,
              );
            }),
          ],
        ),
      ),
    );
  }

  /// Builds podium visualization for top 3 finishers
  Widget _buildPodium(BuildContext context, List<RacerWithResult> results) {
    final first = results[0];
    final second = results.length > 1 ? results[1] : null;
    final third = results.length > 2 ? results[2] : null;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        // 2nd place
        if (second != null)
          _buildPodiumPlace(
            context,
            2,
            second.racer.name,
            second.result.time,
            Colors.grey[600]!,
            100,
          ),

        // 1st place (taller)
        _buildPodiumPlace(
          context,
          1,
          first.racer.name,
          first.result.time,
          Colors.amber[700]!,
          130,
        ),

        // 3rd place
        if (third != null)
          _buildPodiumPlace(
            context,
            3,
            third.racer.name,
            third.result.time,
            Colors.brown[400]!,
            80,
          ),
      ],
    );
  }

  Widget _buildPodiumPlace(
    BuildContext context,
    int place,
    String name,
    double time,
    Color color,
    double height,
  ) {
    return Column(
      children: [
        // Medal icon
        Container(
          width: 50,
          height: 50,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
          child: Center(
            child: Text(
              '$place',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        // Name
        SizedBox(
          width: 100,
          child: Text(
            name,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(height: 4),
        // Time
        Text(
          '${time.toStringAsFixed(3)}s',
          style: const TextStyle(
            fontFamily: 'RobotoMono',
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        // Podium block
        Container(
          width: 100,
          height: height,
          decoration: BoxDecoration(
            color: color.withOpacity(0.2),
            border: Border.all(color: color, width: 2),
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(8),
            ),
          ),
          child: Center(
            child: Text(
              _getPlaceOrdinal(place),
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildResultRow(
    BuildContext context,
    String name,
    int carNumber,
    int place,
    double time,
    double speed,
  ) {
    final placeColor = _getPlaceColor(place);

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          // Place badge
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: placeColor,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '$place',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
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
                  name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                  ),
                ),
                Text(
                  '#$carNumber',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),

          // Time and speed
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${time.toStringAsFixed(3)}s',
                style: const TextStyle(
                  fontFamily: 'RobotoMono',
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (speed > 0)
                Text(
                  '${speed.toStringAsFixed(1)} km/h',
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 12,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
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
        return AppColors.slateGray;
    }
  }

  String _getPlaceOrdinal(int place) {
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
