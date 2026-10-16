import 'package:flutter/material.dart';
import '../core/config/api_config.dart';
import '../core/theme/app_theme.dart';
import '../models/career_note.dart';
import '../models/user_profile.dart';
import '../services/auth_service.dart';
import '../services/firestore_service.dart';
import '../services/github_service.dart';
import '../services/profile_service.dart';
import 'widgets/state_views.dart';

class ProfileScreen extends StatefulWidget {
  final ProfileService profileService;
  final GithubService githubService;
  final AuthService authService;
  final FirestoreService? firestoreService;

  const ProfileScreen({
    super.key,
    required this.profileService,
    required this.githubService,
    required this.authService,
    this.firestoreService,
  });

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  StudentProfile? _profile;
  bool _isLoading = false;
  String? _errorMessage;

  final _githubPatController = TextEditingController();
  bool _isConnectingGithub = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  @override
  void dispose() {
    _githubPatController.dispose();
    super.dispose();
  }

  Future<void> _loadProfile() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final p = await widget.profileService.getMyProfile();
      setState(() => _profile = p);
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _connectGithub() async {
    final token = _githubPatController.text.trim();
    if (token.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a GitHub personal access token.')),
      );
      return;
    }

    setState(() => _isConnectingGithub = true);

    try {
      await widget.githubService.connect(personalAccessToken: token);
      await widget.githubService.triggerAnalysis();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('GitHub connected & codebase analysis triggered!')),
      );
      _githubPatController.clear();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('GitHub connection error: $e')),
      );
    } finally {
      if (mounted) setState(() => _isConnectingGithub = false);
    }
  }

  void _showAddNoteDialog() {
    final titleCtrl = TextEditingController();
    final contentCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Career Study Note'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Title / Topic')),
            const SizedBox(height: 10),
            TextField(
              controller: contentCtrl,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Key Insights / Code Snippet'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final title = titleCtrl.text.trim();
              final content = contentCtrl.text.trim();
              if (title.isNotEmpty && content.isNotEmpty && widget.firestoreService != null) {
                await widget.firestoreService!.addCareerNote(
                  title: title,
                  content: content,
                  tags: ['study', 'career'],
                );
                if (ctx.mounted) Navigator.pop(ctx);
              }
            },
            child: const Text('Save to Firestore'),
          ),
        ],
      ),
    );
  }

  void _showEditProfileDialog() {
    final nameCtrl = TextEditingController(text: _profile?.fullName ?? 'Student');
    final headlineCtrl = TextEditingController(text: _profile?.headline ?? 'Aspiring Software Engineer');
    final institutionCtrl = TextEditingController(text: _profile?.institutionName ?? 'IIT / NIT / University');
    final fieldCtrl = TextEditingController(text: _profile?.fieldOfStudy ?? 'Computer Science');
    final rolesCtrl = TextEditingController(text: _profile?.targetRoles.join(', ') ?? 'Backend Engineer');

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit Career Profile'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Full Name')),
              const SizedBox(height: 10),
              TextField(controller: headlineCtrl, decoration: const InputDecoration(labelText: 'Headline')),
              const SizedBox(height: 10),
              TextField(controller: institutionCtrl, decoration: const InputDecoration(labelText: 'Institution')),
              const SizedBox(height: 10),
              TextField(controller: fieldCtrl, decoration: const InputDecoration(labelText: 'Field of Study')),
              const SizedBox(height: 10),
              TextField(controller: rolesCtrl, decoration: const InputDecoration(labelText: 'Target Roles (comma-separated)')),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final newRoles = rolesCtrl.text.split(',').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();

              final updated = (_profile ?? StudentProfile(
                firebaseUid: widget.authService.currentUid ?? 'student',
                fullName: nameCtrl.text.trim(),
              )).copyWith(
                fullName: nameCtrl.text.trim(),
                headline: headlineCtrl.text.trim(),
                institutionName: institutionCtrl.text.trim(),
                fieldOfStudy: fieldCtrl.text.trim(),
                targetRoles: newRoles,
              );

              final messenger = ScaffoldMessenger.of(context);
              try {
                if (_profile == null) {
                  final created = await widget.profileService.createProfile(updated);
                  if (mounted) setState(() => _profile = created);
                } else {
                  final saved = await widget.profileService.updateProfile(updated);
                  if (mounted) setState(() => _profile = saved);
                }
              } catch (e) {
                messenger.showSnackBar(
                  SnackBar(content: Text('Failed to save profile: $e')),
                );
              }
            },
            child: const Text('Save Changes'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile & Settings', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: AppTheme.errorColor),
            onPressed: () => widget.authService.signOut(),
            tooltip: 'Sign Out',
          ),
        ],
      ),
      body: _isLoading
          ? const LoadingView(message: 'Loading career profile...')
          : _errorMessage != null && _profile == null
              ? ErrorStateView(message: _errorMessage!, onRetry: _loadProfile)
              : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Profile Header Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 32,
                                backgroundColor: AppTheme.primaryColor.withOpacity(0.15),
                                child: Text(
                                  (_profile?.fullName.isNotEmpty == true ? _profile!.fullName[0] : 'S').toUpperCase(),
                                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: AppTheme.primaryColor),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _profile?.fullName ?? 'Student Profile',
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      _profile?.headline ?? 'Aspiring Engineer',
                                      style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'UID: ${widget.authService.currentUid ?? "demo"}',
                                      style: TextStyle(color: Colors.grey.shade500, fontSize: 11),
                                    ),
                                  ],
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.edit_outlined),
                                onPressed: _showEditProfileDialog,
                                tooltip: 'Edit Profile',
                              ),
                            ],
                          ),
                          if (_profile?.targetRoles.isNotEmpty == true) ...[
                            const Divider(height: 24),
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Target Roles: ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                                Expanded(
                                  child: Wrap(
                                    spacing: 6,
                                    children: _profile!.targetRoles.map((r) => Chip(
                                      label: Text(r, style: const TextStyle(fontSize: 11)),
                                      padding: EdgeInsets.zero,
                                      visualDensity: VisualDensity.compact,
                                    )).toList(),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // GitHub Codebase Integration Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.code, color: AppTheme.primaryColor),
                              SizedBox(width: 8),
                              Text('GitHub Codebase Integration', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Connect your GitHub repositories to extract verifiable code evidence for your Career Twin.',
                            style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                          ),
                          const SizedBox(height: 14),
                          TextField(
                            controller: _githubPatController,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'GitHub Personal Access Token (PAT)',
                              hintText: 'ghp_...',
                              prefixIcon: Icon(Icons.key_outlined),
                            ),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton.icon(
                            onPressed: _isConnectingGithub ? null : _connectGithub,
                            icon: const Icon(Icons.sync),
                            label: Text(_isConnectingGithub ? 'Connecting & Analyzing...' : 'Connect & Analyze Repos'),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Cloud Firestore Notes & Preferences Card
                  if (widget.firestoreService != null) ...[
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Row(
                                  children: [
                                    Icon(Icons.cloud_sync_outlined, color: AppTheme.primaryColor),
                                    SizedBox(width: 8),
                                    Text('Cloud Firestore Study Notes', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                                  ],
                                ),
                                IconButton(
                                  icon: const Icon(Icons.add_circle_outline, color: AppTheme.primaryColor),
                                  onPressed: _showAddNoteDialog,
                                  tooltip: 'Add Note',
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Real-time, user-isolated document storage under users/${widget.authService.currentUid ?? "uid"}/career_notes.',
                              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                            ),
                            const Divider(height: 20),
                            StreamBuilder<List<CareerNote>>(
                              stream: widget.firestoreService!.getCareerNotesStream(),
                              builder: (context, snapshot) {
                                final notes = snapshot.data ?? [];
                                if (notes.isEmpty) {
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(vertical: 8.0),
                                    child: Text(
                                      'No Firestore notes yet. Tap + to record your interview prep or code notes.',
                                      style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
                                    ),
                                  );
                                }
                                return Column(
                                  children: notes.take(3).map((note) {
                                    return ListTile(
                                      contentPadding: EdgeInsets.zero,
                                      dense: true,
                                      title: Text(note.title, style: const TextStyle(fontWeight: FontWeight.bold)),
                                      subtitle: Text(note.content, maxLines: 2, overflow: TextOverflow.ellipsis),
                                      trailing: IconButton(
                                        icon: const Icon(Icons.delete_outline, size: 18),
                                        onPressed: () => widget.firestoreService!.deleteCareerNote(note.id),
                                      ),
                                    );
                                  }).toList(),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Observability & System Diagnostics Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.monitor_heart_outlined, color: AppTheme.secondaryColor),
                              SizedBox(width: 8),
                              Text('System Observability & Services', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                            ],
                          ),
                          const Divider(height: 20),
                          _buildDiagRow('Backend Host', ApiConfig.apiBaseUrl),
                          _buildDiagRow('Firebase Project', ApiConfig.firebaseProjectId),
                          _buildDiagRow('LangSmith Project', 'kuru-career-twin'),
                          _buildDiagRow('Active LLM Agent', 'Qwen2.5-3B-Instruct (4-bit)'),
                          _buildDiagRow('Auth Isolation', 'Per-User UID Cryptographic Token'),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 32),
                ],
              ),
            ),
    );
  }

  Widget _buildDiagRow(String title, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
        ],
      ),
    );
  }
}
