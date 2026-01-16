import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/race/race_poll_provider.dart';

class ConnectionIndicator extends ConsumerWidget {
  const ConnectionIndicator({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pollStream = ref.watch(racePollStreamProvider());

    return pollStream.when(
      data: (response) {
        // Connected - show green indicator
        return Tooltip(
          message: 'Connected to DerbyNet server',
          child: Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: Colors.green,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.green.withOpacity(0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
        );
      },
      loading: () {
        // Connecting - show pulsing yellow indicator
        return Tooltip(
          message: 'Connecting to server...',
          child: _PulsingIndicator(
            color: Colors.orange,
          ),
        );
      },
      error: (error, stack) {
        // Error - show red indicator
        return Tooltip(
          message: 'Connection error: ${error.toString().replaceAll('Exception: ', '')}',
          child: Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: Colors.red,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.red.withOpacity(0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _PulsingIndicator extends StatefulWidget {
  final Color color;

  const _PulsingIndicator({required this.color});

  @override
  State<_PulsingIndicator> createState() => _PulsingIndicatorState();
}

class _PulsingIndicatorState extends State<_PulsingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.3, end: 1.0).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: widget.color.withOpacity(_animation.value),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: widget.color.withOpacity(_animation.value * 0.5),
                blurRadius: 4,
                spreadRadius: 1,
              ),
            ],
          ),
        );
      },
    );
  }
}
