import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class AgentStep {
  final String id;
  final String title;
  final String description;
  final IconData icon;

  const AgentStep({
    required this.id,
    required this.title,
    required this.description,
    required this.icon,
  });
}

/// Visual timeline of the 9 logical agents in the Kuru Career Twin LangGraph pipeline.
class AgentStepTimeline extends StatelessWidget {
  final List<String> completedSteps;
  final String? currentRunningStep;
  final bool isWaitingApproval;

  static const List<AgentStep> allAgents = [
    AgentStep(
      id: 'career_profile',
      title: '1. Career Profile Agent',
      description: 'Consolidates profile, education, and target roles',
      icon: Icons.person_outline,
    ),
    AgentStep(
      id: 'github_analysis',
      title: '2. GitHub Analysis Agent',
      description: 'Extracts verified, evidence-backed skills & code graph',
      icon: Icons.code,
    ),
    AgentStep(
      id: 'job_matching',
      title: '3. Job Matching Agent',
      description: 'Matches real Indian job/internship market listings',
      icon: Icons.work_outline,
    ),
    AgentStep(
      id: 'skill_gap',
      title: '4. Skill Gap Agent',
      description: 'Identifies missing skills prioritized by market demand',
      icon: Icons.trending_up,
    ),
    AgentStep(
      id: 'career_planning',
      title: '5. Career Planning Agent',
      description: 'Synthesizes weekly milestone roadmap & what-if trajectories',
      icon: Icons.calendar_month_outlined,
    ),
    AgentStep(
      id: 'resource_research',
      title: '6. Resource Research Agent',
      description: 'Finds genuine documentation and verified learning sources',
      icon: Icons.menu_book_outlined,
    ),
    AgentStep(
      id: 'project_recommendation',
      title: '7. Project Recommendation Agent',
      description: 'Generates targeted portfolio projects closing real gaps',
      icon: Icons.lightbulb_outline,
    ),
    AgentStep(
      id: 'resume',
      title: '8. Resume Agent',
      description: 'Tailors ATS resume bullets based on verified code evidence',
      icon: Icons.description_outlined,
    ),
    AgentStep(
      id: 'approval_gate',
      title: '9. Approval Workflow Agent',
      description: 'Human-in-the-loop decision gate before consequential actions',
      icon: Icons.verified_user_outlined,
    ),
  ];

  const AgentStepTimeline({
    super.key,
    required this.completedSteps,
    this.currentRunningStep,
    this.isWaitingApproval = false,
  });

  bool _isStepCompleted(String stepId) {
    return completedSteps.any((s) => s.contains(stepId));
  }

  bool _isStepRunning(String stepId) {
    return currentRunningStep != null && currentRunningStep!.contains(stepId);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(allAgents.length, (index) {
        final agent = allAgents[index];
        final completed = _isStepCompleted(agent.id);
        final running = _isStepRunning(agent.id);
        final isApprovalPaused = isWaitingApproval && agent.id == 'approval_gate';

        Color statusColor;
        Widget statusBadge;

        if (isApprovalPaused) {
          statusColor = AppTheme.warningColor;
          statusBadge = Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.warningColor.withOpacity(0.2),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Text('Action Required', style: TextStyle(color: AppTheme.warningColor, fontSize: 11, fontWeight: FontWeight.bold)),
          );
        } else if (completed) {
          statusColor = AppTheme.accentColor;
          statusBadge = const Icon(Icons.check_circle, color: AppTheme.accentColor, size: 20);
        } else if (running) {
          statusColor = AppTheme.primaryColor;
          statusBadge = const SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(strokeWidth: 2.5),
          );
        } else {
          statusColor = Colors.grey.shade400;
          statusBadge = Icon(Icons.circle_outlined, color: Colors.grey.shade400, size: 18);
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Column(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.12),
                    shape: BoxShape.circle,
                    border: Border.all(color: statusColor, width: 1.5),
                  ),
                  child: Icon(agent.icon, color: statusColor, size: 18),
                ),
                if (index < allAgents.length - 1)
                  Container(
                    width: 2,
                    height: 28,
                    color: completed ? AppTheme.accentColor.withOpacity(0.5) : Colors.grey.shade300,
                  ),
              ],
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(top: 2, bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          agent.title,
                          style: TextStyle(
                            fontWeight: (completed || running) ? FontWeight.bold : FontWeight.w500,
                            color: completed ? Colors.black87 : Colors.grey.shade800,
                            fontSize: 14,
                          ),
                        ),
                        statusBadge,
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      agent.description,
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      }),
    );
  }
}
