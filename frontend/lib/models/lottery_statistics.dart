class LotteryStatistics {
  final Map<int, int> numberFrequency;
  final List<int> hotNumbers;
  final List<int> coldNumbers;
  final List<double> recentTrends;
  final List<int> overdueNumbers;
  final Map<int, double> trendScores;
  final Map<int, double> momentumScores;

  const LotteryStatistics({
    required this.numberFrequency,
    required this.hotNumbers,
    required this.coldNumbers,
    required this.recentTrends,
    this.overdueNumbers = const [],
    this.trendScores = const {},
    this.momentumScores = const {},
  });

  factory LotteryStatistics.fromJson(Map<String, dynamic> json) {
    final rawFrequency = json['number_frequency'];
    final frequency = <int, int>{};
    if (rawFrequency is Map) {
      rawFrequency.forEach((key, value) {
        final number = int.tryParse(key.toString());
        if (number != null && value is num) frequency[number] = value.toInt();
      });
    }
    List<int> numbers(String key) => json[key] is List
        ? (json[key] as List).whereType<num>().map((n) => n.toInt()).toList()
        : const [];
    List<double> trends = json['recent_trends'] is List
        ? (json['recent_trends'] as List)
            .whereType<num>()
            .map((n) => n.toDouble())
            .toList()
        : const [];
    Map<int, double> scores(String key) {
      final value = json[key];
      if (value is! Map) return const {};
      return {
        for (final entry in value.entries)
          if (int.tryParse(entry.key.toString()) != null && entry.value is num)
            int.parse(entry.key.toString()): (entry.value as num).toDouble(),
      };
    }

    return LotteryStatistics(
      numberFrequency: frequency,
      hotNumbers: numbers('hot_numbers'),
      coldNumbers: numbers('cold_numbers'),
      recentTrends: trends,
      overdueNumbers: numbers('overdue_numbers'),
      trendScores: scores('trend_scores'),
      momentumScores: scores('momentum_scores'),
    );
  }

  Map<String, dynamic> toJson() => {
        'number_frequency': numberFrequency
            .map((key, value) => MapEntry(key.toString(), value)),
        'hot_numbers': hotNumbers,
        'cold_numbers': coldNumbers,
        'recent_trends': recentTrends,
        'overdue_numbers': overdueNumbers,
        'trend_scores': trendScores.map(
          (key, value) => MapEntry(key.toString(), value),
        ),
        'momentum_scores': momentumScores.map(
          (key, value) => MapEntry(key.toString(), value),
        ),
      };
}
