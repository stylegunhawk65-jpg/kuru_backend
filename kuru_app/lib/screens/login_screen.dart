import 'package:flutter/material.dart';
import '../core/config/api_config.dart';
import '../core/theme/app_theme.dart';
import '../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  final AuthService authService;

  const LoginScreen({super.key, required this.authService});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController(text: 'student@kuru.ai');
  final _passwordController = TextEditingController(text: 'Pass1234!');
  final _tokenController = TextEditingController();
  final _uidController = TextEditingController(text: 'kuru_student_demo_101');
  final _customUrlController = TextEditingController(text: ApiConfig.apiBaseUrl);

  bool _isSignUpMode = false;
  bool _isLoading = false;
  String? _errorMessage;
  bool _showTokenInput = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _tokenController.dispose();
    _uidController.dispose();
    _customUrlController.dispose();
    super.dispose();
  }

  Future<void> _handleEmailAuth() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || !email.contains('@')) {
      setState(() => _errorMessage = 'Please provide a valid email address.');
      return;
    }
    if (password.length < 6) {
      setState(() => _errorMessage = 'Password must be at least 6 characters.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      if (_isSignUpMode) {
        await widget.authService.signUpWithEmailAndPassword(
          email: email,
          password: password,
        );
      } else {
        await widget.authService.signInWithEmailAndPassword(
          email: email,
          password: password,
        );
      }
    } catch (e) {
      setState(() => _errorMessage = 'Authentication error: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleDevLogin() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await widget.authService.signInWithDevSession(
        uid: _uidController.text.trim(),
        email: _emailController.text.trim(),
      );
    } catch (e) {
      setState(() => _errorMessage = 'Failed to initialize session: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleTokenLogin() async {
    final token = _tokenController.text.trim();
    if (token.isEmpty) {
      setState(() => _errorMessage = 'Please provide a valid Firebase ID token.');
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      await widget.authService.signInWithToken(
        firebaseIdToken: token,
        uid: _uidController.text.trim(),
        email: _emailController.text.trim(),
      );
    } catch (e) {
      setState(() => _errorMessage = 'Authentication error: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _applyCustomBaseUrl() {
    final url = _customUrlController.text.trim();
    ApiConfig.setCustomBaseUrl(url.isNotEmpty ? url : null);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('API base URL updated to: ${ApiConfig.apiBaseUrl}')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isExpired = widget.authService.status == AuthStatus.expired;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // App Icon & Brand
                  Center(
                    child: Container(
                      width: 72,
                      height: 72,
                      decoration: BoxDecoration(
                        color: AppTheme.primaryColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: const Icon(Icons.rocket_launch, size: 40, color: AppTheme.primaryColor),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Kuru Career Twin',
                    style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Firebase Authentication & Cloud Firestore • Project: ${ApiConfig.firebaseProjectId}',
                    style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 28),

                  if (isExpired) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.warningColor.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.warningColor.withOpacity(0.4)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.info_outline, color: AppTheme.warningColor),
                          SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'Your previous session has expired. Sign in to reconnect with FastAPI.',
                              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  if (_errorMessage != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.errorColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: AppTheme.errorColor, fontSize: 13),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // 1. Email & Password Authentication Card
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Icon(
                                _isSignUpMode ? Icons.person_add_outlined : Icons.lock_outline,
                                color: AppTheme.primaryColor,
                                size: 22,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                _isSignUpMode ? 'Create Student Account' : 'Sign In with Firebase',
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          TextField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            decoration: const InputDecoration(
                              labelText: 'Email Address',
                              prefixIcon: Icon(Icons.email_outlined),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _passwordController,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'Password',
                              prefixIcon: Icon(Icons.key_outlined),
                            ),
                          ),
                          const SizedBox(height: 18),
                          ElevatedButton(
                            onPressed: _isLoading ? null : _handleEmailAuth,
                            child: _isLoading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                  )
                                : Text(_isSignUpMode ? 'Register & Sign In' : 'Sign In'),
                          ),
                          const SizedBox(height: 8),
                          TextButton(
                            onPressed: () => setState(() => _isSignUpMode = !_isSignUpMode),
                            child: Text(
                              _isSignUpMode
                                  ? 'Already have an account? Sign In'
                                  : 'New to Kuru? Create an Account',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // 2. Quick One-Click Dev Session
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.flash_on, color: AppTheme.accentColor, size: 20),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text('Quick Connect (Student Demo)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Instantly connects with local developer profile without waiting for email setup.',
                            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton(
                            onPressed: _isLoading ? null : _handleDevLogin,
                            child: const Text('Enter Career Twin Workspace'),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 12),

                  // 3. Option to provide raw Firebase Token & Custom Backend URL
                  TextButton.icon(
                    onPressed: () => setState(() => _showTokenInput = !_showTokenInput),
                    icon: Icon(_showTokenInput ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down),
                    label: Text(_showTokenInput ? 'Hide Advanced Token Settings' : 'Advanced Token & URL Settings'),
                  ),

                  if (_showTokenInput) ...[
                    const SizedBox(height: 8),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            TextField(
                              controller: _customUrlController,
                              decoration: InputDecoration(
                                labelText: 'Backend API Base URL',
                                hintText: 'http://10.0.2.2:8000/api/v1',
                                suffixIcon: IconButton(
                                  icon: const Icon(Icons.check),
                                  onPressed: _applyCustomBaseUrl,
                                  tooltip: 'Save URL',
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _uidController,
                              decoration: const InputDecoration(labelText: 'Firebase UID'),
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _tokenController,
                              maxLines: 2,
                              decoration: const InputDecoration(
                                labelText: 'Bearer ID Token',
                                hintText: 'Paste Firebase JWT Token...',
                              ),
                            ),
                            const SizedBox(height: 16),
                            OutlinedButton(
                              onPressed: _isLoading ? null : _handleTokenLogin,
                              child: const Text('Sign In with Token'),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
