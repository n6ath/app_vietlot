import 'package:flutter/material.dart';

import 'app_card.dart';

class StatisticCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color? color;

  const StatisticCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final iconColor = color ?? Theme.of(context).colorScheme.primary;

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 180;
        return AppCard(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: compact ? 16 : 18,
                backgroundColor: iconColor.withValues(alpha: 0.12),
                foregroundColor: iconColor,
                child: Icon(icon, size: compact ? 18 : 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      value,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                            fontSize: compact ? 14 : null,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      label,
                      maxLines: 2,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontSize: compact ? 11 : null,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
