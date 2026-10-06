import 'package:flutter/foundation.dart';

import '../models/analysis_models.dart';
import '../models/lottery_result.dart';
import '../models/lottery_statistics.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';

class AppProvider extends ChangeNotifier {
  AppProvider({ApiService? apiService, bool autoLoad = true})
      : apiService = apiService ?? ApiService(baseUrl: defaultApiBaseUrl) {
    if (autoLoad) {
      loadGame();
    }
  }

  final ApiService apiService;
  bool isDarkMode = false;
  String apiBaseUrl = defaultApiBaseUrl;
  String selectedGame = '6_45';
  bool isLoading = false;
  String? errorMessage;
  List<LotteryResult> results = const [];
  LotteryResult? latest;
  LotteryStatistics? statistics;
  List<NumberGroup> pairs = const [];
  List<NumberGroup> triplets = const [];
  Prediction prediction = const Prediction();
  int _loadGeneration = 0;

  LotteryResult? get latestResult =>
      latest ?? (results.isEmpty ? null : results.first);

  Future<void> loadGame([String? game]) async {
    if (game != null) selectedGame = game;
    final generation = ++_loadGeneration;
    debugPrint('[STATE] loading game=$selectedGame');
    isLoading = true;
    errorMessage = null;
    notifyListeners();
    try {
      final loaded = await Future.wait([
        apiService.fetchHistory(selectedGame),
        apiService.fetchLatest(selectedGame),
        apiService.fetchStatistics(selectedGame),
        apiService.fetchPairs(selectedGame),
        apiService.fetchTriplets(selectedGame),
        apiService.fetchPrediction(selectedGame),
      ]);
      if (generation != _loadGeneration) return;
      results = loaded[0] as List<LotteryResult>;
      latest = loaded[1] as LotteryResult? ??
          (results.isEmpty ? null : results.first);
      statistics = loaded[2] as LotteryStatistics;
      pairs = loaded[3] as List<NumberGroup>;
      triplets = loaded[4] as List<NumberGroup>;
      prediction = loaded[5] as Prediction;
      debugPrint(
        '[STATE] loaded game=$selectedGame '
        'history=${results.length} pairs=${pairs.length} '
        'triplets=${triplets.length}',
      );
    } on ApiException catch (error) {
      if (generation != _loadGeneration) return;
      debugPrint('[STATE] API error game=$selectedGame: ${error.message}');
      errorMessage = error.message;
      results = const [];
      latest = null;
      statistics = null;
      pairs = const [];
      triplets = const [];
      prediction = const Prediction();
    } catch (error, stackTrace) {
      if (generation != _loadGeneration) return;
      debugPrint(
        '[STATE] unexpected error while loading $selectedGame: $error',
      );
      debugPrintStack(stackTrace: stackTrace);
      errorMessage = 'Không thể tải dữ liệu từ máy chủ.';
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  void setDarkMode(bool value) {
    isDarkMode = value;
    notifyListeners();
  }

  void setApiBaseUrl(String value) {
    apiBaseUrl = value.trim();
    apiService.baseUrl = apiBaseUrl;
    notifyListeners();
  }

  @override
  void dispose() {
    apiService.dispose();
    super.dispose();
  }
}
