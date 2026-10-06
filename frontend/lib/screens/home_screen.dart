import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_provider.dart';
import '../utils/app_routes.dart';
import '../widgets/app_card.dart';
import '../widgets/result_card.dart';
import '../widgets/statistic_card.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  static const games = <String, String>{
    '5_35': 'Vietlott 5/35',
    '6_45': 'Mega 6/45',
    '6_55': 'Power 6/55',
  };

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    final selectedIndex = games.keys.toList().indexOf(provider.selectedGame);
    return DefaultTabController(
      length: games.length,
      initialIndex: selectedIndex < 0 ? 1 : selectedIndex,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Vietlott AI'),
          bottom: TabBar(
            isScrollable: true,
            onTap: (index) => provider.loadGame(games.keys.elementAt(index)),
            tabs: games.values.map((name) => Tab(text: name)).toList(),
          ),
          actions: [
            IconButton(
              tooltip: 'Cài đặt',
              icon: const Icon(Icons.settings_outlined),
              onPressed: () => Navigator.pushNamed(context, AppRoutes.settings),
            ),
          ],
        ),
        body: TabBarView(
          children: games.keys.map((game) => _GameView(game: game)).toList(),
        ),
      ),
    );
  }
}

class _GameView extends StatelessWidget {
  final String game;
  const _GameView({required this.game});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<AppProvider>();
    final active = provider.selectedGame == game;
    final stats = active ? provider.statistics : null;
    final result = active ? provider.latestResult : null;
    return LayoutBuilder(
      builder: (context, constraints) => ListView(
        padding: EdgeInsets.all(constraints.maxWidth < 360 ? 14 : 20),
        children: [
          Text('Thống kê $game',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 6),
          const Text(
              'Dữ liệu lịch sử giúp tham khảo, không đảm bảo kết quả tương lai.'),
          const SizedBox(height: 16),
          if (active && provider.isLoading)
            const Center(
                child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ))
          else if (active && result != null)
            ResultCard(result: result)
          else if (active)
            Text(provider.errorMessage ?? 'Chưa có dữ liệu mới nhất.'),
          const SizedBox(height: 16),
          Text('Tổng quan', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
                child: StatisticCard(
                    label: 'Số kỳ quay',
                    value: '${active ? provider.results.length : 0}',
                    icon: Icons.history)),
            const SizedBox(width: 10),
            Expanded(
                child: StatisticCard(
                    label: 'Số nóng',
                    value: '${stats?.hotNumbers.length ?? 0}',
                    icon: Icons.local_fire_department_outlined,
                    color: Colors.orange)),
          ]),
          const SizedBox(height: 16),
          const _NavigationCard(
              title: 'Lịch sử kết quả',
              subtitle: 'Xem các kỳ quay gần đây',
              icon: Icons.confirmation_number_outlined,
              route: AppRoutes.results),
          const _NavigationCard(
              title: 'Thống kê',
              subtitle: 'Tần suất, xu hướng và số trễ',
              icon: Icons.bar_chart_outlined,
              route: AppRoutes.statistics),
          const _NavigationCard(
              title: 'Phân tích',
              subtitle: 'Cặp, bộ ba và F1/F2/F3',
              icon: Icons.auto_awesome_outlined,
              route: AppRoutes.analysis),
        ],
      ),
    );
  }
}

class _NavigationCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final String route;
  const _NavigationCard(
      {required this.title,
      required this.subtitle,
      required this.icon,
      required this.route});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: AppCard(
          onTap: () => Navigator.pushNamed(context, route),
          child: Row(children: [
            Icon(icon, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 14),
            Expanded(
                child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
                ])),
            const Icon(Icons.chevron_right),
          ]),
        ),
      );
}
