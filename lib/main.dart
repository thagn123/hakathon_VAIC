import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'core/rm_workspace_core.dart';
import 'core/controllers/employee_workspace_controller.dart';
import 'design/design.dart';
import 'features/queue/queue_screen.dart';
import 'features/case_detail/case_detail_screen.dart';
import 'features/approval/approval_screen.dart';
import 'features/employee_workspace/employee_workspace_screen.dart';
import 'features/credit_requests/credit_requests_screen.dart';
import 'features/auth/login_screen.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => CaseController()),
        ChangeNotifierProvider(create: (_) => CaseDetailController()),
        ChangeNotifierProvider(create: (_) => EmployeeWorkspaceController()),
      ],
      child: const RMWorkspaceApp(),
    ),
  );
}

class RMWorkspaceApp extends StatelessWidget {
  const RMWorkspaceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'RM Workspace',
      debugShowCheckedModeBanner: false,
      theme: lightTheme(),
      darkTheme: darkTheme(),
      routerConfig: _router,
    );
  }
}

final GoRouter _router = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(
      path: '/login',
      name: 'login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/queue',
      name: 'queue',
      builder: (context, state) => const QueueScreen(),
    ),
    GoRoute(
      path: '/case/:caseId',
      name: 'case-detail',
      builder: (context, state) {
        final caseId = state.pathParameters['caseId']!;
        return CaseDetailScreen(caseId: caseId);
      },
    ),
    GoRoute(
      path: '/approval/:caseId',
      name: 'approval',
      builder: (context, state) {
        final caseId = state.pathParameters['caseId']!;
        return ApprovalScreen(caseId: caseId);
      },
    ),
    GoRoute(
      path: '/employee-workspace',
      name: 'employee-workspace',
      builder: (context, state) => const EmployeeWorkspaceScreen(),
    ),
    GoRoute(
      path: '/credit-requests',
      name: 'credit-requests',
      builder: (context, state) => const CreditRequestsScreen(),
    ),
  ],
);

