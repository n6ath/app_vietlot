import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';

import '../providers/app_provider.dart';
import '../widgets/app_card.dart';

class StatisticsScreen extends StatelessWidget {
  const StatisticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AppProvider>();
    final s = p.statistics;
    return Scaffold(
      appBar: AppBar(title: Text('Thống kê ${p.selectedGame}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _section(context, 'Số xuất hiện nhiều', s?.hotNumbers ?? const []),
          _section(context, 'Số xuất hiện ít', s?.coldNumbers ?? const []),
          _section(context, 'Số lâu chưa về', s?.overdueNumbers ?? const []),
          AppCard(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text('Tần suất từng số',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 10),
                Text(s == null || s.numberFrequency.isEmpty
                    ? 'Chưa có dữ liệu'
                    : s.numberFrequency.entries
                        .map((e) => '${e.key}: ${e.value} lần')
                        .join('  •  ')),
              ])),
          const SizedBox(height: 12),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Xu hướng gần đây',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 180,
                  child: LineChart(
                    LineChartData(
                      minY: 0,
                      gridData: const FlGridData(show: false),
                      borderData: FlBorderData(show: false),
                      titlesData: const FlTitlesData(
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 24,
                          ),
                        ),
                        rightTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        topTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(showTitles: false),
                        ),
                      ),
                      lineBarsData: [
                        LineChartBarData(
                          spots: (s?.recentTrends ?? const <double>[])
                              .asMap()
                              .entries
                              .map(
                                (entry) => FlSpot(
                                  entry.key.toDouble(),
                                  entry.value,
                                ),
                              )
                              .toList(),
                          isCurved: true,
                          dotData: const FlDotData(show: false),
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _section(BuildContext context, String title, List<int> numbers) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: AppCard(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(numbers.isEmpty ? 'Chưa có dữ liệu' : numbers.join(' • ')),
        ])),
      );
}
