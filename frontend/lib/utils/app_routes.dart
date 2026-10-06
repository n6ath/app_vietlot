import 'package:flutter/material.dart';

import '../screens/analysis_screen.dart';
import '../screens/home_screen.dart';
import '../screens/results_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/statistics_screen.dart';

class AppRoutes {
  static const home = '/';
  static const results = '/results';
  static const statistics = '/statistics';
  static const analysis = '/analysis';
  static const settings = '/settings';

  static Map<String, WidgetBuilder> get routes => {
        home: (_) => const HomeScreen(),
        results: (_) => const ResultsScreen(),
        statistics: (_) => const StatisticsScreen(),
        analysis: (_) => const AnalysisScreen(),
        settings: (_) => const SettingsScreen(),
      };
}
