import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/analysis_models.dart';
import '../models/lottery_result.dart';
import '../models/lottery_statistics.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;
  const ApiException(this.message, {this.statusCode});
  @override
  String toString() => message;
}

class ApiService {
  String baseUrl;
  final http.Client _client;
  final Duration timeout;

  ApiService({
    required this.baseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 12),
  }) : _client = client ?? http.Client();

  Uri _uri(String path, String gameType) {
    final root = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return Uri.parse('$root/api/$path')
        .replace(queryParameters: {'game_type': gameType});
  }

  Future<dynamic> _get(String path, String gameType) async {
    final uri = _uri(path, gameType);
    debugPrint('[API] GET $uri');
    try {
      final response = await _client.get(uri).timeout(timeout);
      debugPrint(
        '[API] status=${response.statusCode} '
        'bodyLength=${response.body.length}',
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        debugPrint('[API] errorBody=${_preview(response.body)}');
        throw ApiException('Lỗi máy chủ (${response.statusCode})',
            statusCode: response.statusCode);
      }
      if (response.body.trim().isEmpty) return null;
      final decoded = jsonDecode(response.body);
      debugPrint('[API] decodedType=${decoded.runtimeType}');
      return decoded;
    } on TimeoutException {
      debugPrint('[API] timeout $uri');
      throw const ApiException(
          'Yêu cầu hết thời gian. Hãy kiểm tra máy chủ API.');
    } on FormatException {
      debugPrint('[API] invalid JSON $uri');
      throw const ApiException('API trả về dữ liệu không hợp lệ.');
    } on http.ClientException catch (error) {
      debugPrint('[API] clientError $uri: ${error.message}');
      throw ApiException('Không thể kết nối API: ${error.message}');
    }
  }

  Future<List<LotteryResult>> fetchHistory(String gameType) async {
    final payload = await _get('history', gameType);
    final values = payload is List
        ? payload
        : (payload is Map ? payload['results'] : null);
    if (values is! List) return const [];
    final results = <LotteryResult>[];
    for (final item in values.whereType<Map>()) {
      try {
        results.add(LotteryResult.fromJson(item.cast<String, dynamic>()));
      } on FormatException catch (error) {
        debugPrint('[PARSE] bỏ qua kết quả không hợp lệ: $error');
      }
    }
    debugPrint('[PARSE] history parsed successfully: ${results.length} items');
    return results;
  }

  Future<LotteryResult?> fetchLatest(String gameType) async {
    final payload = await _get('latest', gameType);
    final value = payload is Map && payload['result'] is Map
        ? payload['result']
        : payload;
    LotteryResult? result;
    if (value is Map) {
      try {
        result = LotteryResult.fromJson(value.cast<String, dynamic>());
      } on FormatException catch (error) {
        debugPrint('[PARSE] latest không hợp lệ: $error');
      }
    }
    debugPrint('[PARSE] latest parsed successfully: ${result != null}');
    return result;
  }

  Future<List<LotteryResult>> fetchResults([String gameType = '6_45']) =>
      fetchHistory(gameType);

  Future<LotteryStatistics> fetchStatistics(String gameType) async {
    final payload = await _get('statistics', gameType);
    final result = LotteryStatistics.fromJson(
        payload is Map ? payload.cast<String, dynamic>() : const {});
    debugPrint(
      '[PARSE] statistics parsed successfully: '
      'hot=${result.hotNumbers.length} cold=${result.coldNumbers.length} '
      'overdue=${result.overdueNumbers.length}',
    );
    return result;
  }

  Future<List<NumberGroup>> fetchPairs(String gameType) async {
    final groups = _groups(await _get('pairs', gameType), 'pair');
    debugPrint('[PARSE] pairs parsed successfully: ${groups.length} items');
    return groups;
  }

  Future<List<NumberGroup>> fetchTriplets(String gameType) async {
    final groups = _groups(await _get('triplets', gameType), 'triplet');
    debugPrint('[PARSE] triplets parsed successfully: ${groups.length} items');
    return groups;
  }

  Future<Prediction> fetchPrediction(String gameType) async {
    final payload = await _get('prediction', gameType);
    final result = Prediction.fromJson(
        payload is Map ? payload.cast<String, dynamic>() : const {});
    debugPrint(
      '[PARSE] prediction parsed successfully: '
      'f1=${result.f1.length} f2=${result.f2.length} '
      'f3=${result.f3.length} special=${result.special.length}',
    );
    return result;
  }

  String _preview(String body) {
    final normalized = body.replaceAll(RegExp(r'\s+'), ' ').trim();
    return normalized.length <= 500
        ? normalized
        : '${normalized.substring(0, 500)}...';
  }

  List<NumberGroup> _groups(dynamic payload, String key) {
    final values = payload is List
        ? payload
        : (payload is Map ? (payload['${key}s'] ?? payload['items']) : null);
    if (values is! List) return const [];
    return values
        .whereType<Map>()
        .map((item) => NumberGroup.fromJson(item.cast<String, dynamic>(), key))
        .toList();
  }

  void dispose() => _client.close();
}
