import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api/api_endpoints.dart';
import '../core/models/job_match.dart';
import 'core_providers.dart';

/// Loads the user's scored job matches (`GET /api/jobs/matches`, agents service
/// via nginx). An empty list is a normal "no matches yet" state, not an error.
class JobsController extends AsyncNotifier<List<JobMatch>> {
  @override
  Future<List<JobMatch>> build() => _load();

  Future<List<JobMatch>> _load() async {
    try {
      final data = await ref.read(apiClientProvider).get(ApiEndpoints.jobMatches);
      final list = data is Map && data['matches'] is List ? data['matches'] as List : const [];
      return list
          .whereType<Map>()
          .map((m) => JobMatch.fromJson(Map<String, dynamic>.from(m)))
          .toList();
    } catch (_) {
      return const [];
    }
  }

  /// Pull-to-refresh.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(_load);
  }

  /// Updates one match's status (applied / reviewing / rejected / …).
  Future<void> setStatus(int id, String status) async {
    await ref.read(apiClientProvider).post(ApiEndpoints.jobMatchStatus(id), body: {'status': status});
    await refresh();
  }

  /// Triggers a fresh scrape+score run, then reloads.
  Future<void> runSearch() async {
    await ref.read(apiClientProvider).get(ApiEndpoints.jobsRun);
    await refresh();
  }
}

/// Job matches provider.
final jobsProvider = AsyncNotifierProvider<JobsController, List<JobMatch>>(JobsController.new);
