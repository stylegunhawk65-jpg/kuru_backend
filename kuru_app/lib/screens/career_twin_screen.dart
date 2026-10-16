import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/agent_workflow.dart';
import '../services/agent_workflow_service.dart';
import 'widgets/agent_step_timeline.dart';
import 'widgets/state_views.dart';

class CareerTwinScreen extends StatefulWidget {
  final AgentWorkflowService workflowService;

  const CareerTwinScreen({super.key, required this.workflowService});

  @override
  State<CareerTwinScreen> createState() => _CareerTwinScreenState();
}

class _CareerTwinScreenState extends State<CareerTwinScreen> {
  final _roleController = TextEditingController(text: 'Backend Engineer');
  int _weeklyHours = 12;

  bool _isRunning = false;
  String? _errorMessage;
  List<String> _stepHistory = [];

  List<RoadmapMilestone> _milestones = [];
  List<RecommendedProject> _projects = [];
  Map<String, dynamic> _resources = {};
  bool _waitingApproval = false;

  @override
  void dispose() {
    _roleController.dispose();
    super.dispose();
  }

  Future<void> _runFullWorkflow() async {
    setState(() {
      _isRunning = true;
      _errorMessage = null;
      _stepHistory = ['workflow_initiated'];
      _waitingApproval = false;
    });

    try {
      final res = await widget.workflowService.runFullCareerTwin(
        targetRole: _roleController.text.trim(),
        weeklyHours: _weeklyHours,
        actionToQueue: 'submit_application',
      );

      final state = (res['final_state'] as Map<String, dynamic>?) ?? {};
      final history = (state['step_history'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

      // Extract roadmap milestones
      final plan = state['career_plan'] as Map<String, dynamic>?;
      final rawMilestones = (plan?['milestones'] as List<dynamic>?) ?? [];
      final parsedMilestones = rawMilestones.map((m) => RoadmapMilestone.fromJson(m as Map<String, dynamic>)).toList();

      // Extract recommended projects
      final rawProjects = (state['projects'] as List<dynamic>?) ?? [];
      final parsedProjects = rawProjects.map((p) => RecommendedProject.fromJson(p as Map<String, dynamic>)).toList();

      // Extract resources
      final rawRes = (state['resources'] as Map<String, dynamic>?) ?? {};

      final isApprovalPending = state['approval_status'] == 'pending';

      setState(() {
        _stepHistory = history.isNotEmpty ? history : ['career_profile', 'github_analysis', 'job_matching', 'skill_gap', 'career_planning', 'resource_research', 'project_recommendation', 'resume', 'approval_gate'];
        _milestones = parsedMilestones;
        _projects = parsedProjects;
        _resources = rawRes;
        _waitingApproval = isApprovalPending;
      });
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) setState(() => _isRunning = false);
    }
  }

  Future<void> _runRoadmapOnly() async {
    setState(() {
      _isRunning = true;
      _errorMessage = null;
    });

    try {
      final res = await widget.workflowService.runRoadmapSubworkflow(
        targetRole: _roleController.text.trim(),
        weeklyHours: _weeklyHours,
      );

      final state = (res['final_state'] as Map<String, dynamic>?) ?? {};
      final plan = state['career_plan'] as Map<String, dynamic>?;
      final rawMilestones = (plan?['milestones'] as List<dynamic>?) ?? [];
      final parsedMilestones = rawMilestones.map((m) => RoadmapMilestone.fromJson(m as Map<String, dynamic>)).toList();

      final rawProjects = (state['projects'] as List<dynamic>?) ?? [];
      final parsedProjects = rawProjects.map((p) => RecommendedProject.fromJson(p as Map<String, dynamic>)).toList();

      setState(() {
        _stepHistory = (state['step_history'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];
        _milestones = parsedMilestones;
        _projects = parsedProjects;
      });
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) setState(() => _isRunning = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Career Twin AI', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => _showAgentInfoDialog(context),
            tooltip: 'About 9-Agent System',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Controls Card
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'AI Multi-Agent Pipeline Orchestrator',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Coordinates LangGraph agents across your profile, GitHub code, Indian job listings, and skill gaps.',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          flex: 2,
                          child: TextField(
                            controller: _roleController,
                            decoration: const InputDecoration(
                              labelText: 'Target Career Role',
                              prefixIcon: Icon(Icons.psychology),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<int>(
                            initialValue: _weeklyHours,
                            decoration: const InputDecoration(labelText: 'Weekly Hours'),
                            items: [6, 10, 12, 15, 20].map((h) => DropdownMenuItem(value: h, child: Text('$h hrs/wk'))).toList(),
                            onChanged: (val) {
                              if (val != null) setState(() => _weeklyHours = val);
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: _isRunning ? null : _runFullWorkflow,
                            icon: const Icon(Icons.play_arrow),
                            label: Text(_isRunning ? 'Orchestrating...' : 'Run Full 9-Agent Twin'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        OutlinedButton.icon(
                          onPressed: _isRunning ? null : _runRoadmapOnly,
                          icon: const Icon(Icons.map_outlined),
                          label: const Text('Roadmap Only'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              ErrorStateView(
                message: _errorMessage!,
                onRetry: _runFullWorkflow,
              ),
            ],

            const SizedBox(height: 20),

            // 9-Agent Live Progress Timeline
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Agent Workflow Execution', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                        if (_isRunning)
                          const Row(
                            children: [
                              SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                              SizedBox(width: 8),
                              Text('Running...', style: TextStyle(color: AppTheme.primaryColor, fontSize: 12, fontWeight: FontWeight.bold)),
                            ],
                          ),
                      ],
                    ),
                    const Divider(height: 24),
                    AgentStepTimeline(
                      completedSteps: _stepHistory,
                      currentRunningStep: _isRunning ? 'running' : null,
                      isWaitingApproval: _waitingApproval,
                    ),
                  ],
                ),
              ),
            ),

            // Generated Roadmap Milestones
            if (_milestones.isNotEmpty) ...[
              const SizedBox(height: 20),
              const Text('Personalized Career Roadmap', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 10),
              ..._milestones.map((m) => Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: AppTheme.primaryColor.withOpacity(0.12),
                        child: Text('W${m.weekNumber}', style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.primaryColor)),
                      ),
                      title: Text(m.title, style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: 4),
                          Text(m.description),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 6,
                            children: m.focusSkills
                                .map((s) => Chip(
                                      label: Text(s, style: const TextStyle(fontSize: 11)),
                                      padding: EdgeInsets.zero,
                                      visualDensity: VisualDensity.compact,
                                    ))
                                .toList(),
                          ),
                        ],
                      ),
                      trailing: Text('${m.estimatedHours}h', style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
                    ),
                  )),
            ],

            // Recommended Projects
            if (_projects.isNotEmpty) ...[
              const SizedBox(height: 20),
              const Text('Recommended Portfolio Projects', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 10),
              ..._projects.map((p) => Card(
                    margin: const EdgeInsets.only(bottom: 12),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(p.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.secondaryColor.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(p.difficulty.toUpperCase(), style: const TextStyle(color: AppTheme.secondaryColor, fontSize: 10, fontWeight: FontWeight.bold)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(p.description, style: TextStyle(color: Colors.grey.shade700, fontSize: 13)),
                          if (p.architectureHint.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text('Architecture: ${p.architectureHint}', style: TextStyle(fontStyle: FontStyle.italic, color: Colors.grey.shade600, fontSize: 12)),
                          ],
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 6,
                            children: p.targetSkills
                                .map((s) => Chip(
                                      label: Text(s, style: const TextStyle(fontSize: 11)),
                                      backgroundColor: Colors.grey.shade100,
                                      visualDensity: VisualDensity.compact,
                                    ))
                                .toList(),
                          ),
                        ],
                      ),
                    ),
                  )),
            ],

            // Verified Learning Resources
            if (_resources.isNotEmpty) ...[
              const SizedBox(height: 20),
              const Text('Verified Learning Resources', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              const SizedBox(height: 10),
              ..._resources.entries.map((entry) => Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: const Icon(Icons.menu_book, color: AppTheme.secondaryColor),
                      title: Text(entry.key, style: const TextStyle(fontWeight: FontWeight.bold)),
                      subtitle: Text('${(entry.value as List).length} verified documentation sources found'),
                    ),
                  )),
            ],

            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  void _showAgentInfoDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('9 Logical Agents in Kuru'),
        content: const SingleChildScrollView(
          child: Text(
            '1. Career Profile Agent — Consolidates education & target roles\n'
            '2. GitHub Analysis Agent — Code & evidence-backed skills\n'
            '3. Job Matching Agent — Real Indian job listings\n'
            '4. Skill Gap Agent — Market-prioritized skill gaps\n'
            '5. Career Planning Agent — Weekly milestone roadmap\n'
            '6. Resource Research Agent — Genuine documentation links\n'
            '7. Project Recommendation Agent — Targeted gap-closing projects\n'
            '8. Resume Agent — Evidence-grounded tailored bullets\n'
            '9. Approval Workflow Agent — Human-in-the-loop decision gate\n\n'
            'Traces are recorded in LangSmith project "kuru-career-twin".',
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
        ],
      ),
    );
  }
}
