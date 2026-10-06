import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/app_provider.dart';
import 'theme/app_theme.dart';
import 'utils/app_routes.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppProvider(),
      child: const VietlottAiApp(),
    ),
  );
}

class VietlottAiApp extends StatelessWidget {
  const VietlottAiApp({super.key});

  @override
  Widget build(BuildContext context) {
    final isDarkMode = context.watch<AppProvider>().isDarkMode;
    return MaterialApp(
      title: 'Vietlott AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: isDarkMode ? ThemeMode.dark : ThemeMode.light,
      initialRoute: AppRoutes.home,
      routes: AppRoutes.routes,
    );
  }
}
