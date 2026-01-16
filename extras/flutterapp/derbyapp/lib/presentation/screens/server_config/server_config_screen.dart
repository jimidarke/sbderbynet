import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/config/server_config_provider.dart';

class ServerConfigScreen extends ConsumerStatefulWidget {
  const ServerConfigScreen({super.key});

  @override
  ConsumerState<ServerConfigScreen> createState() => _ServerConfigScreenState();
}

class _ServerConfigScreenState extends ConsumerState<ServerConfigScreen> {
  final _formKey = GlobalKey<FormState>();
  final _urlController = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Pre-fill with existing server URL if available
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final serverConfigAsync = ref.read(serverConfigProvider);
      serverConfigAsync.whenData((url) {
        if (url != null && url.isNotEmpty) {
          _urlController.text = url;
        } else {
          // Default to known good value
          _urlController.text = 'http://192.168.100.10/derbynet';
        }
      });
    });
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  String? _validateUrl(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter a server URL';
    }

    // Basic URL validation
    final urlPattern = RegExp(
      r'^https?://[\w\-]+(\.[\w\-]+)*(:\d+)?(/[\w\-\.]*)*/?$',
      caseSensitive: false,
    );

    if (!urlPattern.hasMatch(value)) {
      return 'Please enter a valid URL (e.g., http://192.168.1.100/derbynet)';
    }

    return null;
  }

  Future<void> _saveServerUrl() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() => _isLoading = true);

    try {
      await ref.read(serverConfigProvider.notifier).setServerUrl(
            _urlController.text.trim(),
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Server URL saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save server URL: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final serverConfigAsync = ref.watch(serverConfigProvider);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo/Icon
                  const Icon(
                    Icons.settings_ethernet,
                    size: 80,
                    color: Colors.deepPurple,
                  ),
                  const SizedBox(height: 24),

                  // Title
                  Text(
                    'Server Configuration',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),

                  // Subtitle
                  Text(
                    'Enter the URL of your DerbyNet server',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.grey[600],
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),

                  // Server URL Field
                  TextFormField(
                    controller: _urlController,
                    decoration: const InputDecoration(
                      labelText: 'Server URL',
                      hintText: 'http://192.168.1.100/derbynet',
                      prefixIcon: Icon(Icons.language),
                      border: OutlineInputBorder(),
                      helperText: 'Include http:// or https:// prefix',
                    ),
                    keyboardType: TextInputType.url,
                    textInputAction: TextInputAction.done,
                    validator: _validateUrl,
                    onFieldSubmitted: (_) => _saveServerUrl(),
                  ),
                  const SizedBox(height: 24),

                  // Save Button
                  FilledButton(
                    onPressed: _isLoading ? null : _saveServerUrl,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16.0),
                      child: _isLoading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Colors.white,
                                ),
                              ),
                            )
                          : const Text(
                              'Save and Continue',
                              style: TextStyle(fontSize: 16),
                            ),
                    ),
                  ),

                  // Status indicator
                  if (serverConfigAsync.hasValue && serverConfigAsync.value != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 16.0),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.check_circle,
                            color: Colors.green,
                            size: 16,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Current: ${serverConfigAsync.value}',
                            style: TextStyle(
                              color: Colors.grey[600],
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
