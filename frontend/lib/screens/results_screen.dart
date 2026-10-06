import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../widgets/result_card.dart';

class ResultsScreen extends StatelessWidget {
  const ResultsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AppProvider>();
    return Scaffold(
      appBar: AppBar(title: Text('Lịch sử ${p.selectedGame}')),
      body: p.isLoading
          ? const Center(child: CircularProgressIndicator())
          : p.results.isEmpty
              ? Center(child: Text(p.errorMessage ?? 'Chưa có kết quả.'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: p.results.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (_, index) =>
                      ResultCard(result: p.results[index]),
                ),
    );
  }
}
