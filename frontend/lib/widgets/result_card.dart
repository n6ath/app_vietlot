import 'package:flutter/material.dart';

import '../models/lottery_result.dart';
import 'app_card.dart';

class ResultCard extends StatelessWidget {
  final LotteryResult result;

  const ResultCard({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final date = '${result.drawDate.day.toString().padLeft(2, '0')}/'
        '${result.drawDate.month.toString().padLeft(2, '0')}/'
        '${result.drawDate.year}';

    return LayoutBuilder(
      builder: (context, constraints) {
        final isCompact = constraints.maxWidth < 360;
        final ballRadius = isCompact ? 16.0 : 18.0;

        return AppCard(
          padding: EdgeInsets.symmetric(
            horizontal: isCompact ? 12 : 16,
            vertical: 14,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                result.lotteryType,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 4),
              Text(
                'Kỳ quay $date • ${result.drawNumber}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: isCompact ? 6 : 8,
                runSpacing: isCompact ? 6 : 8,
                children: result.winningNumbers
                    .map(
                      (number) => CircleAvatar(
                        radius: ballRadius,
                        child: Text(
                          number.toString(),
                          style: TextStyle(
                            fontSize: isCompact ? 11 : 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    )
                    .toList(),
              ),
              if (result.specialNumber != null) ...[
                const SizedBox(height: 10),
                Text('Số đặc biệt: ${result.specialNumber}'),
              ],
            ],
          ),
        );
      },
    );
  }
}
