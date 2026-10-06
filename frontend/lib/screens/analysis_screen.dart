import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/analysis_models.dart';
import '../providers/app_provider.dart';
import '../widgets/app_card.dart';

class AnalysisScreen extends StatelessWidget {
  const AnalysisScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AppProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Phân tích')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Phân tích ${p.selectedGame}',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
          _groups(context, 'Cặp số', p.pairs),
          _groups(context, 'Bộ ba số', p.triplets),
          _numbers(context, 'F1 - Ưu tiên cao', p.prediction.f1),
          _numbers(context, 'F2 - Tham khảo', p.prediction.f2),
          _numbers(context, 'F3 - Theo dõi', p.prediction.f3),
          _numbers(context, 'Số đặc biệt', p.prediction.special),
          const SizedBox(height: 8),
          const Text(
              'Các nhóm chỉ phản ánh dữ liệu lịch sử, không phải lời khuyên đầu tư hay dự đoán chắc chắn.'),
        ],
      ),
    );
  }

  Widget _groups(
          BuildContext context, String title, List<NumberGroup> groups) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: AppCard(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (groups.isEmpty)
            const Text('Chưa có dữ liệu')
          else
            Wrap(
                spacing: 8,
                runSpacing: 8,
                children: groups
                    .take(20)
                    .map((group) => Chip(
                        label: Text(
                            '${group.numbers.join(" - ")} (${group.count})')))
                    .toList()),
        ])),
      );

  Widget _numbers(BuildContext context, String title, List<int> numbers) =>
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
