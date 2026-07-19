import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/controllers/employee_workspace_controller.dart';
import '../../design/theme/app_theme.dart';

/// Corporate credit request flow ported from the static RM UI (app/static):
/// customer_user creates the request, RM forwards with a note,
/// credit_specialist gives the final decision. Agents never approve.
class CreditRequestsScreen extends StatefulWidget {
  const CreditRequestsScreen({super.key});

  @override
  State<CreditRequestsScreen> createState() => _CreditRequestsScreenState();
}

class _CreditRequestsScreenState extends State<CreditRequestsScreen> {
  List<Map<String, dynamic>> _rows = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final rows = await context.read<EmployeeWorkspaceController>().api.listCreditRequests();
      setState(() => _rows = rows);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _toast(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<EmployeeWorkspaceController>();
    final role = controller.context?.authorizationContext.primaryRole ?? 'unknown';
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.navy900,
        foregroundColor: Colors.white,
        title: const Text('Yêu cầu tín dụng'),
        actions: [
          Center(child: Padding(padding: const EdgeInsets.only(right: 4), child: Text(role))),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorView(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (role == 'customer_user') ...[
                        _CreateRequestForm(onCreated: (row) {
                          _toast('Đã gửi yêu cầu ${row['request_id']}');
                          _load();
                        }),
                        const SizedBox(height: 16),
                      ],
                      ..._rows.map((row) => _RequestCard(
                            row: row,
                            role: role,
                            onChanged: (message) {
                              _toast(message);
                              _load();
                            },
                          )),
                      if (_rows.isEmpty)
                        const Padding(
                          padding: EdgeInsets.only(top: 48),
                          child: Center(child: Text('Chưa có yêu cầu tín dụng nào.')),
                        ),
                    ],
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
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 60),
          const Icon(Icons.error_outline, size: 48, color: AppColors.error),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 12),
          Center(child: OutlinedButton(onPressed: onRetry, child: const Text('Thử lại'))),
        ],
      );
}

/// One request row. RM sees the forward action on WithRM rows,
/// credit_specialist sees approve/reject on PendingApproval rows.
class _RequestCard extends StatefulWidget {
  final Map<String, dynamic> row;
  final String role;
  final void Function(String message) onChanged;
  const _RequestCard({required this.row, required this.role, required this.onChanged});

  @override
  State<_RequestCard> createState() => _RequestCardState();
}

class _RequestCardState extends State<_RequestCard> {
  final _note = TextEditingController();
  final _reason = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _note.dispose();
    _reason.dispose();
    super.dispose();
  }

  Future<void> _run(Future<Map<String, dynamic>> Function() action, String successMessage) async {
    setState(() => _busy = true);
    try {
      await action();
      widget.onChanged(successMessage);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final row = widget.row;
    final api = context.read<EmployeeWorkspaceController>().api;
    final status = '${row['status'] ?? ''}';
    final requestId = '${row['request_id'] ?? ''}';
    final services = (row['service_recommendation'] as List?) ?? const [];
    final canForward = widget.role == 'rm' && status == 'WithRM';
    final canDecide = widget.role == 'credit_specialist' && status == 'PendingApproval';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('${row['company_name'] ?? ''}',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                ),
                _StatusChip(status: status),
              ],
            ),
            const SizedBox(height: 4),
            Text('$requestId · ${row['request_type']} · ${row['requested_amount_vnd']} VND',
                style: const TextStyle(fontSize: 12, color: AppColors.muted)),
            const SizedBox(height: 8),
            Text('Mục đích: ${row['purpose'] ?? ''}', style: const TextStyle(fontSize: 13)),
            if (row['agent_recommendation'] != null) ...[
              const SizedBox(height: 8),
              Text(
                'Agent đề xuất: ${row['agent_recommendation']} (score ${row['appraisal_score'] ?? '-'}) — chỉ tham khảo, quyết định cuối do chuyên gia.',
                style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: AppColors.muted),
              ),
            ],
            if ('${row['rm_note'] ?? ''}'.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('Ghi chú RM: ${row['rm_note']}', style: const TextStyle(fontSize: 12)),
            ],
            if (services.isNotEmpty) ...[
              const SizedBox(height: 6),
              ...services.map((s) => Text('• ${s['service']} (${s['priority']}): ${s['reason']}',
                  style: const TextStyle(fontSize: 12))),
            ],
            if ('${row['decision_reason'] ?? ''}'.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('Lý do quyết định: ${row['decision_reason']}', style: const TextStyle(fontSize: 12)),
            ],
            if (canForward) ...[
              const SizedBox(height: 10),
              TextField(
                controller: _note,
                decoration: const InputDecoration(labelText: 'Ghi chú của RM (tuỳ chọn)'),
              ),
              const SizedBox(height: 8),
              FilledButton.icon(
                onPressed: _busy
                    ? null
                    : () => _run(
                          () => api.forwardCreditRequest(requestId, _note.text.trim()),
                          'Đã chuyển $requestId lên phê duyệt',
                        ),
                icon: const Icon(Icons.forward_to_inbox),
                label: const Text('Chuyển phê duyệt'),
              ),
            ],
            if (canDecide) ...[
              const SizedBox(height: 10),
              TextField(
                controller: _reason,
                decoration: const InputDecoration(labelText: 'Lý do quyết định (bắt buộc, ≥5 ký tự)'),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: _busy ? null : () => _decide(api, requestId, 'approved'),
                      child: const Text('Phê duyệt'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _busy ? null : () => _decide(api, requestId, 'rejected'),
                      child: const Text('Từ chối'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _busy ? null : () => _decide(api, requestId, 'needs_more_information'),
                      child: const Text('Cần bổ sung'),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _decide(dynamic api, String requestId, String decision) {
    final reason = _reason.text.trim();
    if (reason.length < 5) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Hãy nhập lý do quyết định (ít nhất 5 ký tự).')));
      return;
    }
    _run(() => api.decideCreditRequest(requestId, decision, reason), 'Đã ghi nhận quyết định "$decision" cho $requestId');
  }
}

class _StatusChip extends StatelessWidget {
  final String status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'WithRM' => AppColors.statusNeedInfo,
      'PendingApproval' => AppColors.orange,
      'Approved' => AppColors.statusReady,
      'Rejected' => AppColors.error,
      _ => AppColors.muted,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(999)),
      child: Text(status, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: color)),
    );
  }
}

/// Same fields as CorporateCreditRequestCreate — mirrors the static UI form.
class _Field {
  final String key, label;
  final bool number;
  final bool optional;
  const _Field(this.key, this.label, {this.number = false, this.optional = false});
}

const List<_Field> _formFields = [
  _Field('company_name', 'Tên doanh nghiệp'),
  _Field('tax_id', 'Mã số thuế'),
  _Field('legal_type', 'Loại hình pháp lý'),
  _Field('representative', 'Người đại diện'),
  _Field('industry', 'Ngành nghề'),
  _Field('business_scale', 'Quy mô kinh doanh'),
  _Field('total_assets_billion_vnd', 'Tổng tài sản (tỷ VND)', number: true),
  _Field('net_revenue_billion_vnd', 'Doanh thu thuần (tỷ VND)', number: true),
  _Field('net_profit_billion_vnd', 'Lợi nhuận ròng (tỷ VND)', number: true),
  _Field('debt_to_equity_ratio', 'Hệ số nợ/vốn chủ', number: true),
  _Field('cic_debt_classification', 'Phân loại nợ CIC'),
  _Field('current_debt_billion_vnd', 'Dư nợ hiện tại (tỷ VND)', number: true),
  _Field('collateral_description', 'Mô tả tài sản bảo đảm'),
  _Field('collateral_value_billion_vnd', 'Giá trị TSBĐ (tỷ VND)', number: true),
  _Field('casa_avg_balance_billion_vnd', 'Số dư CASA bình quân (tỷ VND)', number: true),
  _Field('repayment_history', 'Lịch sử trả nợ'),
  _Field('requested_amount_vnd', 'Số tiền đề nghị (VND)', number: true),
  _Field('requested_term_months', 'Kỳ hạn (tháng)', number: true, optional: true),
  _Field('purpose', 'Mục đích sử dụng vốn'),
];

class _CreateRequestForm extends StatefulWidget {
  final void Function(Map<String, dynamic> row) onCreated;
  const _CreateRequestForm({required this.onCreated});

  @override
  State<_CreateRequestForm> createState() => _CreateRequestFormState();
}

class _CreateRequestFormState extends State<_CreateRequestForm> {
  final Map<String, TextEditingController> _controllers = {
    for (final f in _formFields) f.key: TextEditingController(),
  };
  String _requestType = 'loan';
  bool _busy = false;

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    final controller = context.read<EmployeeWorkspaceController>();
    final scope = controller.context?.authorizationContext.customerScope ?? const [];
    final payload = <String, dynamic>{
      'customer_id': scope.isNotEmpty ? scope.first : '',
      'request_type': _requestType,
    };
    for (final f in _formFields) {
      final raw = _controllers[f.key]!.text.trim();
      if (raw.isEmpty) {
        if (f.optional) {
          payload[f.key] = null;
          continue;
        }
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Thiếu trường: ${f.label}')));
        return;
      }
      payload[f.key] = f.number ? num.tryParse(raw) : raw;
      if (f.number && payload[f.key] == null) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${f.label} phải là số')));
        return;
      }
    }
    setState(() => _busy = true);
    try {
      final row = await controller.api.createCreditRequest(payload);
      widget.onCreated(row);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ExpansionTile(
        title: const Text('Tạo yêu cầu tín dụng mới', style: TextStyle(fontWeight: FontWeight.w800)),
        subtitle: const Text('Nhập hồ sơ doanh nghiệp — agent chỉ thẩm định sơ bộ, không phê duyệt.'),
        childrenPadding: const EdgeInsets.all(14),
        children: [
          for (final f in _formFields) ...[
            TextField(
              controller: _controllers[f.key],
              keyboardType: f.number ? const TextInputType.numberWithOptions(decimal: true, signed: true) : null,
              maxLines: f.key == 'purpose' ? 3 : 1,
              decoration: InputDecoration(labelText: f.optional ? '${f.label} (tuỳ chọn)' : f.label),
            ),
            const SizedBox(height: 10),
          ],
          Row(
            children: [
              const Text('Loại yêu cầu:  '),
              for (final t in const ['loan', 'service', 'both'])
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: ChoiceChip(
                    label: Text(t),
                    selected: _requestType == t,
                    onSelected: (_) => setState(() => _requestType = t),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _busy ? null : _submit,
              icon: _busy
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send),
              label: Text(_busy ? 'Đang gửi...' : 'Gửi yêu cầu'),
            ),
          ),
        ],
      ),
    );
  }
}
