import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../core/controllers/employee_workspace_controller.dart';
import '../../core/models/employee_models.dart';
import '../../design/design.dart';

/// Role-Aware Employee Copilot workspace: real /api/v2/me/* calls, not
/// the /api/v1 case-queue mock path the rest of this app currently uses.
/// See docs/ROLE_AWARE_P0_FIX_IMPLEMENTATION_REPORT.md "Flutter wiring".
class EmployeeWorkspaceScreen extends StatefulWidget {
  const EmployeeWorkspaceScreen({super.key});

  @override
  State<EmployeeWorkspaceScreen> createState() => _EmployeeWorkspaceScreenState();
}

class _EmployeeWorkspaceScreenState extends State<EmployeeWorkspaceScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<EmployeeWorkspaceController>().refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<EmployeeWorkspaceController>(
      builder: (context, controller, _) => Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          backgroundColor: AppColors.navy900,
          foregroundColor: Colors.white,
          title: const Text('Employee Copilot'),
          actions: [
            if (controller.context != null)
              Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Center(child: Text(controller.context!.authorizationContext.primaryRole)),
              ),
            IconButton(
              icon: const Icon(Icons.request_page_outlined),
              tooltip: 'Yêu cầu tín dụng',
              onPressed: () => context.push('/credit-requests'),
            ),
            IconButton(
              icon: const Icon(Icons.logout),
              tooltip: 'Đăng xuất',
              onPressed: () {
                controller.logout();
                context.go('/login');
              },
            ),
          ],
        ),
        body: RefreshIndicator(
          onRefresh: controller.refresh,
          child: controller.isLoading
              ? const Center(child: CircularProgressIndicator())
              : controller.error != null
                  ? _ErrorView(message: controller.error!, onRetry: controller.refresh)
                  : _WorkspaceBody(controller: controller),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 80),
        const Icon(Icons.error_outline, size: 48, color: AppColors.statusBlocked),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Text(message, textAlign: TextAlign.center),
        ),
        const SizedBox(height: 12),
        Center(child: OutlinedButton(onPressed: onRetry, child: const Text('Thử lại'))),
      ],
    );
  }
}

class _WorkspaceBody extends StatelessWidget {
  final EmployeeWorkspaceController controller;
  const _WorkspaceBody({required this.controller});

  @override
  Widget build(BuildContext context) {
    final ctx = controller.context;
    if (ctx == null) return const SizedBox.shrink();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
      children: [
        _WelcomeHeader(ctx: ctx),
        const SizedBox(height: 14),
        _TodaySummary(ctx: ctx, controller: controller),
        const SizedBox(height: 20),
        if (controller.isManager)
          _ManagerDashboard(workload: controller.teamWorkload)
        else ...[
          const _SectionTitle(icon: Icons.task_alt, title: 'Việc cần làm', caption: 'Ưu tiên theo mức độ ảnh hưởng và SLA'),
          _WorkQueueSection(controller: controller),
        ],
        const SizedBox(height: 20),
        _InformationSection(ctx: ctx),
      ],
    );
  }
}

class _WelcomeHeader extends StatelessWidget {
  final EmployeeContext ctx;
  const _WelcomeHeader({required this.ctx});

  String get _roleLabel {
    switch (ctx.authorizationContext.primaryRole) {
      case 'relationship_manager':
        return 'Relationship Manager';
      case 'legal_specialist':
        return 'Legal Specialist';
      case 'product_specialist':
        return 'Product Specialist';
      case 'operations_specialist':
        return 'Operations Specialist';
      case 'manager':
        return 'Sales Manager';
      default:
        return ctx.authorizationContext.primaryRole;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.navy900, AppColors.navy700]),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 27,
            backgroundColor: AppColors.orange,
            child: Text(ctx.employeeId.substring(0, 1), style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w900)),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Workspace của bạn', style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 3),
                Text(ctx.employeeId, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
                const SizedBox(height: 3),
                Text(_roleLabel, style: const TextStyle(color: Colors.white, fontSize: 13)),
              ],
            ),
          ),
          const Icon(Icons.verified_user_outlined, color: AppColors.statusReady, size: 26),
        ],
      ),
    );
  }
}

class _TodaySummary extends StatelessWidget {
  final EmployeeContext ctx;
  final EmployeeWorkspaceController controller;
  const _TodaySummary({required this.ctx, required this.controller});

  @override
  Widget build(BuildContext context) {
    final critical = controller.workQueue.where((item) => item.priority == 'high').length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle(icon: Icons.dashboard_customize_outlined, title: 'Tổng quan nhanh', caption: 'Thông tin bạn cần trước khi bắt đầu'),
        const SizedBox(height: 10),
        LayoutBuilder(
          builder: (context, constraints) {
            final columns = constraints.maxWidth >= 420 ? 3 : 2;
            final width = (constraints.maxWidth - ((columns - 1) * 8)) / columns;
            return Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                SizedBox(width: width, child: _MetricCard(icon: Icons.priority_high_rounded, label: 'Ưu tiên cao', value: '$critical', color: AppColors.statusBlocked)),
                SizedBox(width: width, child: _MetricCard(icon: Icons.pending_actions_outlined, label: 'Việc đang chờ', value: '${controller.workQueue.length}', color: AppColors.statusNeedInfo)),
                SizedBox(width: width, child: _MetricCard(icon: Icons.business_outlined, label: 'Khách hàng', value: '${ctx.authorizationContext.customerScope.length}', color: AppColors.blue)),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  const _MetricCard({required this.icon, required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            const SizedBox(height: 2),
            Text(label, maxLines: 2, style: const TextStyle(fontSize: 11, color: AppColors.muted)),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String title;
  final String caption;
  const _SectionTitle({required this.icon, required this.title, required this.caption});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: AppColors.navy700, size: 22),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
              const SizedBox(height: 2),
              Text(caption, style: const TextStyle(fontSize: 12, color: AppColors.muted)),
            ],
          ),
        ),
      ],
    );
  }
}

class _InformationSection extends StatelessWidget {
  final EmployeeContext ctx;
  const _InformationSection({required this.ctx});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle(icon: Icons.info_outline, title: 'Thông tin cần biết', caption: 'Phạm vi dữ liệu và quyền của bạn'),
        const SizedBox(height: 10),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: const CircleAvatar(backgroundColor: AppColors.blue100, child: Icon(Icons.business_outlined, color: AppColors.navy700)),
                title: const Text('Khách hàng được phân công', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: Text(ctx.authorizationContext.customerScope.isEmpty ? 'Chưa có phạm vi' : ctx.authorizationContext.customerScope.join(' · ')),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const CircleAvatar(backgroundColor: AppColors.statusReady100, child: Icon(Icons.verified_outlined, color: AppColors.statusReady)),
                title: const Text('Danh tính đã xác minh', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: const Text('Role và permission được lấy từ SSO/IAM'),
                trailing: ctx.authorizationContext.identityVerified ? const Icon(Icons.check_circle, color: AppColors.statusReady) : const Icon(Icons.warning_amber, color: AppColors.statusNeedInfo),
              ),
              const Divider(height: 1),
              ListTile(
                leading: const CircleAvatar(backgroundColor: AppColors.orange100, child: Icon(Icons.lock_outline, color: AppColors.orange700)),
                title: const Text('Quyền đang có', style: TextStyle(fontWeight: FontWeight.w800)),
                subtitle: Text('${ctx.authorizationContext.permissions.length} quyền được cấp'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}


class _WorkQueueSection extends StatelessWidget {
  final EmployeeWorkspaceController controller;
  const _WorkQueueSection({required this.controller});

  @override
  Widget build(BuildContext context) {
    if (controller.workQueue.isEmpty) {
      return const Padding(
        padding: EdgeInsets.only(top: 32),
        child: Center(child: Text('Không có việc cần ưu tiên.')),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Next Best Work', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 8),
        ...controller.workQueue.map((item) => _WorkItemCard(item: item, controller: controller)),
      ],
    );
  }
}

class _WorkItemCard extends StatelessWidget {
  final WorkQueueItem item;
  final EmployeeWorkspaceController controller;
  const _WorkItemCard({required this.item, required this.controller});

  Color get _priorityColor {
    switch (item.priority) {
      case 'high':
        return AppColors.statusBlocked;
      case 'medium':
        return AppColors.statusNeedInfo;
      default:
        return AppColors.statusAiCta;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  backgroundColor: _priorityColor,
                  child: Text(item.priorityScore.toStringAsFixed(0), style: const TextStyle(color: Colors.white, fontSize: 12)),
                ),
                const SizedBox(width: 12),
                Expanded(child: Text(item.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
                Icon(item.requiresApproval ? Icons.lock_outline : Icons.play_circle_outline, color: item.requiresApproval ? AppColors.statusNeedInfo : AppColors.navy700),
              ],
            ),
            if (item.reasons.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(item.reasons.first, style: const TextStyle(color: AppColors.muted)),
            ],
            if (item.recommendedAction.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('Làm ngay: ${item.recommendedAction}', style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.navy700)),
            ],
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: item.requiresApproval
                  ? OutlinedButton.icon(
                      onPressed: null,
                      icon: const Icon(Icons.lock_outline, size: 18),
                      label: const Text('Cần phê duyệt'),
                    )
                  : FilledButton.tonalIcon(
                      onPressed: () => controller.submitFeedback(item.workItemId, 'accepted'),
                      icon: const Icon(Icons.check_circle_outline, size: 18),
                      label: const Text('Đã xử lý'),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ManagerDashboard extends StatelessWidget {
  final Map<String, dynamic>? workload;
  const _ManagerDashboard({required this.workload});

  @override
  Widget build(BuildContext context) {
    if (workload == null) return const SizedBox.shrink();
    final metrics = (workload!['aggregate_metrics'] as Map?)?.cast<String, dynamic>() ?? {};
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Aggregate Team Workload', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 8),
            Text('Case bị chặn: ${metrics['blocked_cases'] ?? 0}'),
            Text('Rủi ro SLA: ${metrics['sla_risks'] ?? 0}'),
            const SizedBox(height: 8),
            const Text(
              'Chỉ hiển thị số liệu tổng hợp — không có preference/habit cá nhân của từng RM.',
              style: TextStyle(fontStyle: FontStyle.italic, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
