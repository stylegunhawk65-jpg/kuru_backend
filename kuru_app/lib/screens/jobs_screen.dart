import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/job_listing.dart';
import '../services/application_service.dart';
import '../services/jobs_service.dart';
import '../services/resume_service.dart';
import 'widgets/state_views.dart';

class JobsScreen extends StatefulWidget {
  final JobsService jobsService;
  final ApplicationService? applicationService;
  final ResumeService? resumeService;

  const JobsScreen({
    super.key,
    required this.jobsService,
    this.applicationService,
    this.resumeService,
  });

  @override
  State<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends State<JobsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _searchController = TextEditingController();

  List<JobListing> _exploreJobs = [];
  List<JobListing> _savedJobs = [];

  bool _isLoadingExplore = false;
  bool _isLoadingSaved = false;
  String? _exploreError;
  String? _savedError;

  String? _selectedWorkMode;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() {
      if (_tabController.index == 1 && _savedJobs.isEmpty && !_isLoadingSaved) {
        _loadSavedJobs();
      }
    });
    _loadExploreJobs();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadExploreJobs() async {
    setState(() {
      _isLoadingExplore = true;
      _exploreError = null;
    });

    try {
      final jobs = await widget.jobsService.searchJobs(
        query: _searchController.text.trim(),
        workMode: _selectedWorkMode,
      );
      setState(() => _exploreJobs = jobs);
    } catch (e) {
      setState(() => _exploreError = e.toString());
    } finally {
      if (mounted) setState(() => _isLoadingExplore = false);
    }
  }

  Future<void> _loadSavedJobs() async {
    setState(() {
      _isLoadingSaved = true;
      _savedError = null;
    });

    try {
      final jobs = await widget.jobsService.getSavedJobs();
      setState(() => _savedJobs = jobs);
    } catch (e) {
      setState(() => _savedError = e.toString());
    } finally {
      if (mounted) setState(() => _isLoadingSaved = false);
    }
  }

  Future<void> _toggleSave(JobListing job) async {
    try {
      if (job.isSaved) {
        await widget.jobsService.unsaveJob(job.id);
        setState(() {
          _exploreJobs = _exploreJobs.map((j) => j.id == job.id ? j.copyWith(isSaved: false) : j).toList();
          _savedJobs.removeWhere((j) => j.id == job.id);
        });
      } else {
        await widget.jobsService.saveJob(job.id);
        setState(() {
          _exploreJobs = _exploreJobs.map((j) => j.id == job.id ? j.copyWith(isSaved: true) : j).toList();
          _savedJobs.add(job.copyWith(isSaved: true));
        });
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to update saved status: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Jobs & Internships', style: TextStyle(fontWeight: FontWeight.bold)),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppTheme.primaryColor,
          labelColor: AppTheme.primaryColor,
          unselectedLabelColor: Colors.grey.shade600,
          tabs: const [
            Tab(icon: Icon(Icons.search), text: 'Discover'),
            Tab(icon: Icon(Icons.bookmark_outline), text: 'Saved'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Discover Tab
          _buildDiscoverTab(),
          // Saved Tab
          _buildSavedTab(),
        ],
      ),
    );
  }

  Widget _buildDiscoverTab() {
    return Column(
      children: [
        // Search and Filters
        Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            children: [
              TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: 'Search roles, skills, or companies...',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.arrow_forward),
                    onPressed: _loadExploreJobs,
                  ),
                ),
                onSubmitted: (_) => _loadExploreJobs(),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    FilterChip(
                      label: const Text('All Modes'),
                      selected: _selectedWorkMode == null,
                      onSelected: (_) {
                        setState(() => _selectedWorkMode = null);
                        _loadExploreJobs();
                      },
                    ),
                    const SizedBox(width: 6),
                    FilterChip(
                      label: const Text('Remote'),
                      selected: _selectedWorkMode == 'remote',
                      onSelected: (val) {
                        setState(() => _selectedWorkMode = val ? 'remote' : null);
                        _loadExploreJobs();
                      },
                    ),
                    const SizedBox(width: 6),
                    FilterChip(
                      label: const Text('Hybrid'),
                      selected: _selectedWorkMode == 'hybrid',
                      onSelected: (val) {
                        setState(() => _selectedWorkMode = val ? 'hybrid' : null);
                        _loadExploreJobs();
                      },
                    ),
                    const SizedBox(width: 6),
                    FilterChip(
                      label: const Text('On-Site'),
                      selected: _selectedWorkMode == 'on-site',
                      onSelected: (val) {
                        setState(() => _selectedWorkMode = val ? 'on-site' : null);
                        _loadExploreJobs();
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        Expanded(
          child: _isLoadingExplore
              ? const LoadingView(message: 'Searching verified Indian job listings...')
              : _exploreError != null
                  ? ErrorStateView(message: _exploreError!, onRetry: _loadExploreJobs)
                  : _exploreJobs.isEmpty
                      ? EmptyStateView(
                          icon: Icons.work_off_outlined,
                          title: 'No Listings Found',
                          message: 'Try adjusting your search query or filter settings.',
                          actionLabel: 'Refresh',
                          onAction: _loadExploreJobs,
                        )
                      : RefreshIndicator(
                          onRefresh: _loadExploreJobs,
                          child: ListView.builder(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            itemCount: _exploreJobs.length,
                            itemBuilder: (context, index) {
                              return _buildJobCard(_exploreJobs[index]);
                            },
                          ),
                        ),
        ),
      ],
    );
  }

  Widget _buildSavedTab() {
    if (_isLoadingSaved) {
      return const LoadingView(message: 'Loading saved jobs...');
    }
    if (_savedError != null) {
      return ErrorStateView(message: _savedError!, onRetry: _loadSavedJobs);
    }
    if (_savedJobs.isEmpty) {
      return EmptyStateView(
        icon: Icons.bookmark_border,
        title: 'No Saved Jobs Yet',
        message: 'Tap the bookmark icon on any job card to save it for later review.',
        actionLabel: 'Discover Jobs',
        onAction: () => _tabController.animateTo(0),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadSavedJobs,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        itemCount: _savedJobs.length,
        itemBuilder: (context, index) {
          return _buildJobCard(_savedJobs[index]);
        },
      ),
    );
  }

  Widget _buildJobCard(JobListing job) {
    final score = job.matchScore;
    Color scoreColor = Colors.grey;
    if (score != null) {
      if (score >= 75) {
        scoreColor = AppTheme.accentColor;
      } else if (score >= 50) {
        scoreColor = AppTheme.warningColor;
      } else {
        scoreColor = Colors.grey.shade600;
      }
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(job.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 2),
                      Text(job.company, style: TextStyle(color: Colors.grey.shade800, fontWeight: FontWeight.w500)),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          if (job.location != null) ...[
                            Icon(Icons.location_on_outlined, size: 14, color: Colors.grey.shade600),
                            const SizedBox(width: 2),
                            Text(job.location!, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
                            const SizedBox(width: 8),
                          ],
                          if (job.workMode != null)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(color: Colors.grey.shade200, borderRadius: BorderRadius.circular(4)),
                              child: Text(job.workMode!, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: Icon(job.isSaved ? Icons.bookmark : Icons.bookmark_border, color: job.isSaved ? AppTheme.primaryColor : Colors.grey),
                  onPressed: () => _toggleSave(job),
                  tooltip: job.isSaved ? 'Remove from Saved' : 'Save Job',
                ),
              ],
            ),

            if (score != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: scoreColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: scoreColor, width: 1),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.auto_awesome, size: 14, color: scoreColor),
                        const SizedBox(width: 4),
                        Text('${score.toInt()}% Match', style: TextStyle(color: scoreColor, fontWeight: FontWeight.bold, fontSize: 12)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text('Source: ${job.sourcePlatform}', style: TextStyle(color: Colors.grey.shade600, fontSize: 11)),
                ],
              ),
            ],

            if (job.matchedSkills.isNotEmpty || job.missingSkills.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: [
                  ...job.matchedSkills.take(4).map((s) => Chip(
                        label: Text('✓ $s', style: const TextStyle(fontSize: 11, color: AppTheme.accentColor)),
                        backgroundColor: AppTheme.accentColor.withOpacity(0.1),
                        side: BorderSide.none,
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      )),
                  ...job.missingSkills.take(3).map((s) => Chip(
                        label: Text('Missing: $s', style: TextStyle(fontSize: 11, color: Colors.amber.shade900)),
                        backgroundColor: Colors.amber.shade50,
                        side: BorderSide.none,
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      )),
                ],
              ),
            ],

            if (job.matchReasons.isNotEmpty) ...[
              const SizedBox(height: 8),
              ...job.matchReasons.take(2).map((r) => Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text('• $r', style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
                  )),
            ],

            if (widget.applicationService != null) ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  OutlinedButton.icon(
                    icon: const Icon(Icons.assignment_turned_in_outlined, size: 16),
                    label: const Text('Prepare Application'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.primaryColor,
                      visualDensity: VisualDensity.compact,
                    ),
                    onPressed: () => _prepareApplication(job),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _prepareApplication(JobListing job) async {
    if (widget.applicationService == null) return;

    final notesController = TextEditingController();
    final shouldProceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Prepare Application: ${job.company}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Position: ${job.title}',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'This will synthesize a tailored ATS resume strictly grounded in your verified GitHub code and stage an approval request. External submission requires your explicit approval.',
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: notesController,
              decoration: const InputDecoration(
                labelText: 'Personal Notes / Deadline (Optional)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryColor),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Prepare & Queue Approval', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (shouldProceed != true) return;

    try {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Preparing tailored materials and staging approval...')),
      );

      final res = await widget.applicationService!.prepareApplication(
        jobId: job.id,
        notes: notesController.text.trim().isNotEmpty ? notesController.text.trim() : null,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Application packet staged (Approval Request #${res.approvalRequestId})! Review under Approvals tab before submission.',
            ),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to prepare application: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }
}
