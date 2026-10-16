import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/skill_gap.dart';
import '../services/github_service.dart';
import '../services/intelligence_service.dart';
import 'widgets/state_views.dart';

class SkillGapsScreen extends StatefulWidget {
  final GithubService githubService;
  final IntelligenceService intelligenceService;

  const SkillGapsScreen({
    super.key,
    required this.githubService,
    required this.intelligenceService,
  });

  @override
  State<SkillGapsScreen> createState() => _SkillGapsScreenState();
}

class _SkillGapsScreenState extends State<SkillGapsScreen> {
  List<StudentSkill> _skills = [];
  List<PrioritizedSkillGap> _gaps = [];
  WhatIfSimulationResult? _simulationResult;

  bool _isLoading = false;
  bool _isSimulating = false;
  String? _errorMessage;

  final Set<String> _selectedSimulationSkills = {};
  final _roleController = TextEditingController(text: 'Backend Engineer');

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _roleController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final skillsFuture = widget.githubService.getSkills();
      final gapsFuture = widget.intelligenceService.getSkillGaps(targetRole: _roleController.text.trim());

      final results = await Future.wait([skillsFuture, gapsFuture]);
      setState(() {
        _skills = results[0] as List<StudentSkill>;
        _gaps = results[1] as List<PrioritizedSkillGap>;
      });
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _runSimulation() async {
    if (_selectedSimulationSkills.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select at least 1 skill to simulate.')),
      );
      return;
    }

    setState(() {
      _isSimulating = true;
    });

    try {
      final res = await widget.intelligenceService.simulateCareerPath(
        targetRole: _roleController.text.trim(),
        simulatedSkills: _selectedSimulationSkills.toList(),
      );
      setState(() => _simulationResult = res);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Simulation error: $e')),
      );
    } finally {
      if (mounted) setState(() => _isSimulating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Skill Gaps & Simulator', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadData,
            tooltip: 'Reload Skills & Gaps',
          ),
        ],
      ),
      body: _isLoading
          ? const LoadingView(message: 'Analyzing code evidence & skill gaps...')
          : _errorMessage != null
              ? ErrorStateView(message: _errorMessage!, onRetry: _loadData)
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // What-If Simulator Card
                      _buildSimulatorCard(),

                      const SizedBox(height: 20),

                      // Prioritized Skill Gaps
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Prioritized Skill Gaps', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: AppTheme.errorColor.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text('${_gaps.length} Gaps Found', style: const TextStyle(color: AppTheme.errorColor, fontSize: 11, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      if (_gaps.isEmpty)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Text('No skill gaps detected for role "${_roleController.text}".', style: TextStyle(color: Colors.grey.shade600)),
                          ),
                        )
                      else
                        ..._gaps.map((gap) => _buildGapCard(gap)),

                      const SizedBox(height: 24),

                      // Verified Codebase Skills
                      const Text('Verified Codebase Skills', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                      const SizedBox(height: 6),
                      Text('Skills backed by code evidence from your connected repositories.', style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
                      const SizedBox(height: 10),
                      if (_skills.isEmpty)
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Column(
                              children: [
                                const Text('No verified skills found. Connect GitHub to extract code evidence.'),
                                const SizedBox(height: 8),
                                OutlinedButton(
                                  onPressed: () {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('Navigate to Profile tab to connect GitHub.')),
                                    );
                                  },
                                  child: const Text('Connect GitHub in Profile'),
                                ),
                              ],
                            ),
                          ),
                        )
                      else
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _skills.map((s) => _buildSkillChip(s)).toList(),
                        ),

                      const SizedBox(height: 32),
                    ],
                  ),
                ),
    );
  }

  Widget _buildSimulatorCard() {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.bolt, color: AppTheme.primaryColor),
                SizedBox(width: 8),
                Text('What-If Career Simulator', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              'Select skills to acquire and see projected score lift and newly unlocked jobs.',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
            ),
            const SizedBox(height: 12),

            // Selection chips from Gaps
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: _gaps.map((g) {
                final isSelected = _selectedSimulationSkills.contains(g.skillName);
                return FilterChip(
                  label: Text(g.skillName),
                  selected: isSelected,
                  selectedColor: AppTheme.primaryColor.withOpacity(0.18),
                  checkmarkColor: AppTheme.primaryColor,
                  onSelected: (val) {
                    setState(() {
                      if (val) {
                        _selectedSimulationSkills.add(g.skillName);
                      } else {
                        _selectedSimulationSkills.remove(g.skillName);
                      }
                    });
                  },
                );
              }).toList(),
            ),

            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _isSimulating ? null : _runSimulation,
              icon: const Icon(Icons.show_chart),
              label: Text(_isSimulating ? 'Simulating...' : 'Simulate Trajectory'),
            ),

            if (_simulationResult != null) ...[
              const Divider(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildMetric('Baseline', '${_simulationResult!.baselineScore.toInt()}%', Colors.grey.shade700),
                  _buildMetric('Projected', '${_simulationResult!.projectedScore.toInt()}%', AppTheme.accentColor),
                  _buildMetric('Score Lift', '+${_simulationResult!.scoreLift.toInt()}%', AppTheme.primaryColor),
                  _buildMetric('New Jobs', '+${_simulationResult!.newlyEligibleJobsCount}', AppTheme.secondaryColor),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetric(String label, String value, Color color) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 2),
        Text(label, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
      ],
    );
  }

  Widget _buildGapCard(PrioritizedSkillGap gap) {
    Color urgencyColor;
    if (gap.urgency == 'high') {
      urgencyColor = AppTheme.errorColor;
    } else if (gap.urgency == 'medium') {
      urgencyColor = AppTheme.warningColor;
    } else {
      urgencyColor = Colors.grey.shade600;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Row(
          children: [
            Text(gap.skillName, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: urgencyColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(gap.urgency.toUpperCase(), style: TextStyle(color: urgencyColor, fontSize: 10, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(gap.rationale, style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
          ],
        ),
        trailing: Text('In ${gap.demandFrequency} jobs', style: TextStyle(color: Colors.grey.shade500, fontSize: 11)),
      ),
    );
  }

  Widget _buildSkillChip(StudentSkill skill) {
    return Chip(
      avatar: const Icon(Icons.check_circle, size: 16, color: AppTheme.accentColor),
      label: Text('${skill.skillName} (${(skill.confidenceScore * 100).toInt()}%)'),
      backgroundColor: AppTheme.accentColor.withOpacity(0.08),
      side: BorderSide(color: AppTheme.accentColor.withOpacity(0.3)),
    );
  }
}
