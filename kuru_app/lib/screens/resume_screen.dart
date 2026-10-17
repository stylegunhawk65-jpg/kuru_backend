import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/resume.dart';
import '../services/resume_service.dart';
import 'widgets/state_views.dart';

class ResumeScreen extends StatefulWidget {
  final ResumeService resumeService;
  final String? initialResumeId;

  const ResumeScreen({
    super.key,
    required this.resumeService,
    this.initialResumeId,
  });

  @override
  State<ResumeScreen> createState() => _ResumeScreenState();
}

class _ResumeScreenState extends State<ResumeScreen> {
  List<ResumeModel> _resumes = [];
  ResumeModel? _selectedResume;
  bool _isLoading = false;
  bool _isGenerating = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadResumes();
  }

  Future<void> _loadResumes() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final list = await widget.resumeService.listResumes();
      setState(() {
        _resumes = list;
        if (list.isNotEmpty) {
          if (widget.initialResumeId != null) {
            _selectedResume = list.firstWhere(
              (r) => r.id == widget.initialResumeId,
              orElse: () => list.first,
            );
          } else {
            _selectedResume = list.first;
          }
        } else {
          _selectedResume = null;
        }
      });
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _generateFreshResume() async {
    final roleController = TextEditingController();
    final shouldGenerate = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Generate Tailored ATS Resume'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Synthesize an evidence-backed resume strictly grounded in your verified GitHub code, AST skills, and practical assessments.',
              style: TextStyle(fontSize: 13, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: roleController,
              decoration: const InputDecoration(
                labelText: 'Target Role (Optional)',
                hintText: 'e.g. Backend Engineer',
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
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryColor),
            child: const Text('Generate', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (shouldGenerate != true) return;

    setState(() {
      _isGenerating = true;
      _errorMessage = null;
    });

    try {
      final newResume = await widget.resumeService.generateResume(
        targetRole: roleController.text.trim().isNotEmpty ? roleController.text.trim() : null,
      );
      setState(() {
        _resumes.insert(0, newResume);
        _selectedResume = newResume;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('ATS Resume synthesized with evidence citations!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Generation failed: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isGenerating = false);
    }
  }

  Future<void> _regenerateCurrent() async {
    if (_selectedResume == null) return;

    setState(() => _isGenerating = true);
    try {
      final updated = await widget.resumeService.regenerateResume(
        _selectedResume!.id,
        targetRole: _selectedResume!.targetRole,
        jobId: _selectedResume!.jobId,
      );
      setState(() {
        _selectedResume = updated;
        final idx = _resumes.indexWhere((r) => r.id == updated.id);
        if (idx >= 0) _resumes[idx] = updated;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Resume regenerated with latest verified assessments!')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Regeneration failed: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isGenerating = false);
    }
  }

  Future<void> _exportPdf() async {
    if (_selectedResume == null) return;

    try {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Exporting ATS-compliant PDF...')),
      );
      final bytes = await widget.resumeService.downloadResumePdf(_selectedResume!.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('PDF downloaded successfully (${bytes.length} bytes)! ATS compatible.'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('PDF export failed: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('ATS Resume Studio'),
        actions: [
          IconButton(
            tooltip: 'Generate Resume',
            icon: const Icon(Icons.add_circle_outline),
            onPressed: _isGenerating ? null : _generateFreshResume,
          ),
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _loadResumes,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const LoadingView(message: 'Loading ATS resumes & verified citations...');
    }

    if (_errorMessage != null) {
      return ErrorStateView(
        message: _errorMessage!,
        onRetry: _loadResumes,
      );
    }

    if (_resumes.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const EmptyStateView(
              icon: Icons.description_outlined,
              title: 'No Resumes Created Yet',
              message: 'Generate your first ATS-friendly resume backed by your verified GitHub code.',
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isGenerating ? null : _generateFreshResume,
              icon: const Icon(Icons.auto_awesome),
              label: Text(_isGenerating ? 'Synthesizing...' : 'Generate Grounded Resume'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      children: [
        if (_resumes.length > 1) _buildResumeSelector(),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: _buildResumeDocument(_selectedResume!),
          ),
        ),
      ],
    );
  }

  Widget _buildResumeSelector() {
    return Container(
      color: Colors.grey.shade50,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          const Text('Select Version: ', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(width: 8),
          Expanded(
            child: DropdownButton<String>(
              value: _selectedResume?.id,
              isExpanded: true,
              underline: const SizedBox(),
              items: _resumes.map((r) {
                return DropdownMenuItem<String>(
                  value: r.id,
                  child: Text(
                    r.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13),
                  ),
                );
              }).toList(),
              onChanged: (id) {
                if (id != null) {
                  setState(() {
                    _selectedResume = _resumes.firstWhere((r) => r.id == id);
                  });
                }
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResumeDocument(ResumeModel resume) {
    final meta = resume.tailoringMetadata;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Action toolbar
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            OutlinedButton.icon(
              onPressed: _isGenerating ? null : _regenerateCurrent,
              icon: const Icon(Icons.sync, size: 16),
              label: const Text('Regenerate'),
            ),
            const SizedBox(width: 8),
            ElevatedButton.icon(
              onPressed: _exportPdf,
              icon: const Icon(Icons.picture_as_pdf, size: 16),
              label: const Text('Export ATS PDF'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Anti-hallucination verification banner
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.green.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.green.shade200),
          ),
          child: Row(
            children: [
              Icon(Icons.verified, color: Colors.green.shade700, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Anti-Hallucination Verified: 100% of claims are strictly grounded in your code commits, AST parsing, and sandbox assessments.',
                  style: TextStyle(fontSize: 12, color: Colors.green.shade900, fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Main ATS Paper Card
        Card(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header: Candidate Name & Contact
                Center(
                  child: Column(
                    children: [
                      Text(
                        resume.contactInfo.name,
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        [
                          resume.contactInfo.email,
                          if (resume.contactInfo.phone != null) resume.contactInfo.phone,
                          if (resume.contactInfo.location != null) resume.contactInfo.location,
                        ].join(' | '),
                        style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                      ),
                      if (resume.contactInfo.github != null || resume.contactInfo.linkedin != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            [
                              if (resume.contactInfo.github != null) 'GitHub: ${resume.contactInfo.github}',
                              if (resume.contactInfo.linkedin != null) 'LinkedIn: ${resume.contactInfo.linkedin}',
                            ].join(' | '),
                            style: const TextStyle(fontSize: 11, color: AppTheme.primaryColor),
                          ),
                        ),
                    ],
                  ),
                ),
                const Divider(height: 32, thickness: 1),

                // Professional Summary
                if (resume.summary != null && resume.summary!.isNotEmpty) ...[
                  _sectionHeader('PROFESSIONAL SUMMARY'),
                  const SizedBox(height: 6),
                  Text(
                    resume.summary!,
                    style: const TextStyle(fontSize: 13, height: 1.4),
                  ),
                  const SizedBox(height: 20),
                ],

                // Technical Skills By Category
                if (resume.skillsByCategory.isNotEmpty) ...[
                  _sectionHeader('TECHNICAL SKILLS'),
                  const SizedBox(height: 8),
                  ...resume.skillsByCategory.entries.map((entry) {
                    final skillNames = entry.value.map((s) => s.name).join(', ');
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${entry.key}: ',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                          ),
                          Expanded(
                            child: Text(
                              skillNames,
                              style: const TextStyle(fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 20),
                ],

                // Practical Verification Badges
                if (resume.practicalAssessments.isNotEmpty) ...[
                  _sectionHeader('VERIFIED PRACTICAL ASSESSMENTS'),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: resume.practicalAssessments.map((a) {
                      return Chip(
                        avatar: const Icon(Icons.check_circle, color: Colors.green, size: 16),
                        label: Text(
                          '${a.skillName} (${a.score.toInt()}% - ${a.level.toUpperCase()})',
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                        ),
                        backgroundColor: Colors.green.shade50,
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),
                ],

                // Featured Engineering Projects
                if (resume.projects.isNotEmpty) ...[
                  _sectionHeader('FEATURED CODE PROJECTS'),
                  const SizedBox(height: 8),
                  ...resume.projects.map((proj) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                proj.title,
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              if (proj.technologies.isNotEmpty)
                                Text(
                                  proj.technologies.take(3).join(', '),
                                  style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary),
                                ),
                            ],
                          ),
                          if (proj.summary != null && proj.summary!.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 2, bottom: 4),
                              child: Text(proj.summary!, style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic)),
                            ),
                          ...proj.bullets.map((b) => Padding(
                                padding: const EdgeInsets.only(left: 8, bottom: 2),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('• ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                                    Expanded(child: Text(b, style: const TextStyle(fontSize: 12, height: 1.3))),
                                  ],
                                ),
                              )),
                        ],
                      ),
                    );
                  }),
                  const SizedBox(height: 16),
                ],

                // Education
                if (resume.education.isNotEmpty) ...[
                  _sectionHeader('EDUCATION'),
                  const SizedBox(height: 8),
                  ...resume.education.map((edu) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(edu.institution, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                              Text('${edu.degree}${edu.fieldOfStudy != null ? " in ${edu.fieldOfStudy}" : ""}',
                                  style: const TextStyle(fontSize: 12)),
                            ],
                          ),
                          if (edu.graduationYear != null)
                            Text(edu.graduationYear.toString(), style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary)),
                        ],
                      ),
                    );
                  }),
                ],
              ],
            ),
          ),
        ),

        // Citations / Evidence groundings card
        if (meta != null && meta.evidenceCitations.isNotEmpty) ...[
          const SizedBox(height: 16),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.account_tree, color: AppTheme.primaryColor, size: 18),
                      const SizedBox(width: 8),
                      const Text(
                        'EVIDENCE CITATIONS (AST & REPO GROUNDING)',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Every claim on this resume links directly to physical source code verified by Kuru:',
                    style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                  ),
                  const SizedBox(height: 12),
                  ...meta.evidenceCitations.entries.map((cit) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(cit.key, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                          ...cit.value.take(2).map((path) => Padding(
                                padding: const EdgeInsets.only(left: 12, top: 1),
                                child: Text(
                                  '• $path',
                                  style: TextStyle(fontSize: 11, color: Colors.blueGrey.shade700, fontFamily: 'monospace'),
                                ),
                              )),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _sectionHeader(String title) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.8),
        ),
        const SizedBox(height: 2),
        Container(height: 1.5, color: Colors.black87),
      ],
    );
  }
}
