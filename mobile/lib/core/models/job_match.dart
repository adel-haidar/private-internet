import 'json_utils.dart';

/// A scored job match from the job-hunt agent (`GET /api/jobs/matches`).
/// Fields mirror the web `types/jobs.ts` JobMatch; parsing is defensive.
class JobMatch {
  const JobMatch({
    required this.id,
    required this.platform,
    required this.title,
    required this.company,
    required this.location,
    required this.country,
    required this.jobUrl,
    required this.remoteType,
    required this.status,
    required this.matchScore,
    required this.matchTier,
    required this.techFlags,
    this.aiSummary,
    this.salaryRaw,
    this.currency,
  });

  final int id;
  final String platform;
  final String title;
  final String company;
  final String location;
  final String country;
  final String jobUrl;
  final String remoteType;
  final String status; // new | reviewing | applied | interviewing | rejected | …
  final double matchScore; // 0–100
  final String matchTier; // STRONG_MATCH | GOOD_MATCH | WEAK_MATCH
  final List<String> techFlags;
  final String? aiSummary;
  final String? salaryRaw;
  final String? currency;

  factory JobMatch.fromJson(Map<String, dynamic> j) => JobMatch(
        id: asInt(j['id']) ?? 0,
        platform: asStr(j['platform']),
        title: asStr(j['title']),
        company: asStr(j['company']),
        location: asStr(j['location']),
        country: asStr(j['country']),
        jobUrl: asStr(j['job_url']),
        remoteType: asStr(j['remote_type']),
        status: asStr(j['status'], 'new'),
        matchScore: asDouble(j['match_score']) ?? 0,
        matchTier: asStr(j['match_tier'], 'WEAK_MATCH'),
        techFlags: j['tech_flags'] is List
            ? (j['tech_flags'] as List).map((e) => e.toString()).toList()
            : const [],
        aiSummary: asStrOrNull(j['ai_summary']),
        salaryRaw: asStrOrNull(j['salary_raw']),
        currency: asStrOrNull(j['currency']),
      );
}
