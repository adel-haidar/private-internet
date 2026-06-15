import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/i18n/i18n.dart';
import '../../core/models/job_match.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_dimens.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/widgets/toast.dart';
import '../../providers/jobs_provider.dart';

/// Job-hunt matches — the mobile counterpart of the web JobsView. Lists scored
/// matches, opens the posting, lets you update status, and triggers a run.
class JobsScreen extends ConsumerWidget {
  const JobsScreen({super.key});

  static const _statuses = ['new', 'reviewing', 'applied', 'interviewing', 'rejected', 'withdrawn'];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = context.c;
    final jobs = ref.watch(jobsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(ref.t('nav.jobs'), style: AppText.md.copyWith(color: c.textPrimary)),
        actions: [
          IconButton(
            tooltip: 'Find new jobs',
            icon: const Icon(Icons.travel_explore_outlined),
            onPressed: () async {
              AppToast.show(context, 'Searching for new jobs…');
              try {
                await ref.read(jobsProvider.notifier).runSearch();
                if (context.mounted) AppToast.show(context, 'Job search updated');
              } catch (e) {
                if (context.mounted) AppToast.show(context, '$e', isError: true);
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(jobsProvider.notifier).refresh(),
        child: jobs.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(children: [
            Padding(
              padding: const EdgeInsets.all(AppDimens.space6),
              child: Text('Could not load jobs.\n$e',
                  textAlign: TextAlign.center, style: AppText.sm.copyWith(color: c.textSecondary)),
            ),
          ]),
          data: (matches) {
            if (matches.isEmpty) {
              return ListView(children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                      AppDimens.space6, AppDimens.space8, AppDimens.space6, AppDimens.space6),
                  child: Column(
                    children: [
                      Icon(Icons.work_outline, size: 40, color: c.textTertiary),
                      const SizedBox(height: AppDimens.space3),
                      Text('No job matches yet',
                          style: AppText.md.copyWith(color: c.textPrimary), textAlign: TextAlign.center),
                      const SizedBox(height: AppDimens.space2),
                      Text('Tap the search icon to find roles that match your brain.',
                          style: AppText.sm.copyWith(color: c.textSecondary), textAlign: TextAlign.center),
                    ],
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: AppDimens.space2),
              itemCount: matches.length,
              separatorBuilder: (_, __) => Divider(height: 1, color: c.isDark ? c.borderMedium : c.borderSubtle),
              itemBuilder: (_, i) => _JobTile(match: matches[i], statuses: _statuses),
            );
          },
        ),
      ),
    );
  }
}

class _JobTile extends ConsumerWidget {
  const _JobTile({required this.match, required this.statuses});
  final JobMatch match;
  final List<String> statuses;

  Color _tierColor(AppPalette c) {
    switch (match.matchTier) {
      case 'STRONG_MATCH':
        return c.accentPrimary;
      case 'GOOD_MATCH':
        return c.brainAmber;
      default:
        return c.textTertiary;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final c = context.c;
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: AppDimens.space4, vertical: AppDimens.space2),
      title: Text(match.title, style: AppText.base.copyWith(color: c.textPrimary, fontWeight: FontWeight.w600)),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 2),
          Text(
            [match.company, if (match.location.isNotEmpty) match.location].join(' · '),
            style: AppText.sm.copyWith(color: c.textSecondary),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _Chip(label: '${match.matchScore.round()}%', color: _tierColor(c)),
              if (match.status != 'new') _Chip(label: match.status, color: c.textTertiary, outline: true),
              if (match.remoteType.isNotEmpty) _Chip(label: match.remoteType, color: c.textTertiary, outline: true),
            ],
          ),
        ],
      ),
      trailing: PopupMenuButton<String>(
        icon: Icon(Icons.more_vert, color: c.textTertiary),
        onSelected: (s) async {
          if (s == '_open') {
            if (match.jobUrl.isNotEmpty) {
              await launchUrl(Uri.parse(match.jobUrl), mode: LaunchMode.externalApplication);
            }
            return;
          }
          try {
            await ref.read(jobsProvider.notifier).setStatus(match.id, s);
          } catch (e) {
            if (context.mounted) AppToast.show(context, '$e', isError: true);
          }
        },
        itemBuilder: (_) => [
          const PopupMenuItem(value: '_open', child: Text('Open posting')),
          const PopupMenuDivider(),
          for (final s in statuses)
            PopupMenuItem(
              value: s,
              child: Row(
                children: [
                  if (s == match.status) const Icon(Icons.check, size: 16) else const SizedBox(width: 16),
                  const SizedBox(width: 8),
                  Text('Mark $s'),
                ],
              ),
            ),
        ],
      ),
      onTap: match.jobUrl.isEmpty
          ? null
          : () => launchUrl(Uri.parse(match.jobUrl), mode: LaunchMode.externalApplication),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.color, this.outline = false});
  final String label;
  final Color color;
  final bool outline;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: outline ? Colors.transparent : color.withValues(alpha: 0.15),
        border: outline ? Border.all(color: color.withValues(alpha: 0.4)) : null,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(label, style: AppText.xs.copyWith(color: color, fontWeight: FontWeight.w600)),
    );
  }
}
