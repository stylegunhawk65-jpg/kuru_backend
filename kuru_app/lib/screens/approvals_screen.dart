import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/agent_workflow.dart';
import '../services/agent_workflow_service.dart';
import 'widgets/state_views.dart';

class ApprovalsScreen extends StatefulWidget {
  final AgentWorkflowService workflowService;

  const ApprovalsScreen({super.key, required this.workflowService});

  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  List<AgentApprovalRequest> _approvals = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadApprovals();
  }

  Future<void> _loadApprovals() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final list = await widget.workflowService.getPendingApprovals();
      setState(() => _approvals = list);
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitDecision(AgentApprovalRequest approval, bool approved) async {
    final feedbackController = TextEditingController();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(approved ? 'Approve Action' : 'Reject Action'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Are you sure you want to ${approved ? 'approve' : 'reject'} "${approval.actionDescription}"?'),
            const SizedBox(height: 12),
            TextField(
              controller: feedbackController,
              decoration: const InputDecoration(
                labelText: 'Optional Feedback / Instructions',
                hintText: 'e.g., Looks good to proceed...',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: approved ? AppTheme.accentColor : AppTheme.errorColor,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(approved ? 'Confirm Approval' : 'Confirm Rejection'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await widget.workflowService.submitApprovalDecision(
        approvalId: approval.id,
        approved: approved,
        feedback: feedbackController.text.trim().isNotEmpty ? feedbackController.text.trim() : null,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Action ${approved ? 'Approved' : 'Rejected'} successfully.')),
      );
      _loadApprovals();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to submit decision: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Approval Decisions', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadApprovals,
            tooltip: 'Refresh Approvals',
          ),
        ],
      ),
      body: _isLoading
          ? const LoadingView(message: 'Checking pending approval requests...')
          : _errorMessage != null
              ? ErrorStateView(message: _errorMessage!, onRetry: _loadApprovals)
              : _approvals.isEmpty
                  ? EmptyStateView(
                      icon: Icons.task_alt,
                      title: 'All Clear!',
                      message: 'There are no pending consequential actions requiring your human review.',
                      actionLabel: 'Check Again',
                      onAction: _loadApprovals,
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(16.0),
                      itemCount: _approvals.length,
                      itemBuilder: (context, index) {
                        return _buildApprovalCard(_approvals[index]);
                      },
                    ),
    );
  }

  Widget _buildApprovalCard(AgentApprovalRequest approval) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.warningColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.shield_outlined, color: AppTheme.warningColor, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        approval.actionType.replaceAll('_', ' ').toUpperCase(),
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      Text(
                        'Status: ${approval.status.toUpperCase()}',
                        style: const TextStyle(color: AppTheme.warningColor, fontWeight: FontWeight.bold, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              approval.actionDescription,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
            ),
            if (approval.payload.isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: approval.payload.entries.map((e) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Text(
                        '${e.key}: ${e.value}',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: AppTheme.errorColor),
                    onPressed: () => _submitDecision(approval, false),
                    icon: const Icon(Icons.close),
                    label: const Text('Reject'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentColor),
                    onPressed: () => _submitDecision(approval, true),
                    icon: const Icon(Icons.check),
                    label: const Text('Approve & Execute'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
