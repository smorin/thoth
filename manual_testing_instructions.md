 Please run the following tests to verify the response storage fix:

  # First, source the API key
  source openai.env

  # Test 1: Basic query
  ./thoth "What is Python?" --provider openai -v

  # Test 2: Verify file creation
  ls -la *_openai_*.md

  # Test 3: Check file content has response
  cat *_openai_*.md

  # Test 4: Multiple queries (simulating concurrent operations)
  ./thoth "Query 1: What is REST API?" --provider openai
  ./thoth "Query 2: What is GraphQL?" --provider openai

  # Check both files have different content
  ls -la *_openai_*.md

  Manual Testing Instructions for Phase 2

  Please run the following tests to verify timeout functionality:

  Part A: Config-based Timeout Tests

  # Test 1: Normal query (should complete with default 30s timeout)
  source openai.env
  ./thoth "Brief answer: What is 2+2?" --provider openai

  # Test 2: Test with very short timeout in config (should fail)
  cat > test_timeout_config.toml << EOF
  version = "1.0"
  [providers.openai]
  api_key = "\${OPENAI_API_KEY}"
  timeout = 0.1
  EOF

  ./thoth "Explain quantum computing in detail" --provider openai --config
  test_timeout_config.toml

  # Test 3: Test with reasonable longer timeout in config
  cat > test_timeout_config2.toml << EOF
  version = "1.0"
  [providers.openai]
  api_key = "\${OPENAI_API_KEY}"
  timeout = 60
  model = "gpt-4o"
  EOF

  ./thoth "Explain how DNS works" --provider openai --config
  test_timeout_config2.toml -v

  # Clean up
  rm -f test_timeout_config*.toml *_openai_*.md

  Part B: CLI Timeout Override Tests

  # Test 4: CLI override with short timeout (should override default)
  source openai.env
  ./thoth "Explain the theory of relativity" --provider openai --timeout 0.1

  # Test 5: CLI override with long timeout (verbose to see timeout)
  ./thoth "What is 2+2?" --provider openai --timeout 60 -v

  # Test 6: CLI override should take precedence over config
  cat > test_timeout_config3.toml << EOF
  version = "1.0"
  [providers.openai]
  api_key = "\${OPENAI_API_KEY}"
  timeout = 0.1
  EOF

  # This should succeed because CLI timeout=30 overrides config timeout=0.1
  ./thoth "Simple question: What is Python?" --provider openai --config
  test_timeout_config3.toml --timeout 30

  # Test 7: Verify -T short form works
  ./thoth "What is 2+2?" --provider openai -T 15 -v

  # Clean up
  rm -f test_timeout_config*.toml *_openai_*.md

  Expected Results:

  - Test 1: Should complete successfully
  - Test 2: Should fail with "Request timed out. Try increasing timeout in config."
  - Test 3: Should complete, verbose shows "openai Timeout: 60s"
  - Test 4: Should fail with timeout error
  - Test 5: Should complete, verbose shows "openai Timeout: 60.0s"
  - Test 6: Should succeed (CLI overrides config)
  - Test 7: Should work with -T, verbose shows "openai Timeout: 15.0s"

  Once you've verified Phase 2 works correctly, we can proceed to Phase 3 (Enhanced
  Error Handling).



  Phase 3 Complete: Enhanced Error Handling

  I've successfully implemented comprehensive error handling for the OpenAI provider:

  Enhancements Added:

  1. Specific Error Types:
    - httpx.TimeoutException - Request timeout
    - httpx.ConnectError - Connection failures
    - 401 errors - Authentication/API key issues
    - 429 errors - Rate limit exceeded
    - 404 errors - Model not found
    - Quota exceeded errors
    - 400 errors - Invalid requests
  2. Retry Logic:
    - Added @retry decorator using tenacity
    - Retries up to 3 times with exponential backoff
    - Only retries on transient errors (timeout, connection)
  3. Configuration Improvements:
    - Made temperature configurable (default: 0.7)
    - Made max_tokens configurable (default: 4000)

  Manual Testing Instructions for Phase 3

  Please run the following tests to verify error handling:

  # Test 1: Invalid API key
  OPENAI_API_KEY="sk-invalid-key-12345" ./thoth "test" --provider openai

  # Test 2: Empty API key
  OPENAI_API_KEY="" ./thoth "test" --provider openai

  # Test 3: Invalid model
  cat > test_bad_model.toml << EOF
  version = "1.0"
  [providers.openai]
  api_key = "\${OPENAI_API_KEY}"
  model = "gpt-5-does-not-exist"
  EOF

  source openai.env
  ./thoth "test" --provider openai --config test_bad_model.toml

  # Test 4: Test retry on timeout (use very short timeout)
  ./thoth "Explain quantum computing in extreme detail" --provider openai --timeout
  0.5 -v
  # Should see retry attempts in output

  # Test 5: Test configuration of temperature and max_tokens
  cat > test_params.toml << EOF
  version = "1.0"
  [providers.openai]
  api_key = "\${OPENAI_API_KEY}"
  model = "gpt-4o"
  temperature = 0.2
  max_tokens = 100
  EOF

  source openai.env
  ./thoth "Write a very long essay about AI" --provider openai --config
  test_params.toml
  # Should get a short response due to max_tokens=100

  # Test 6: Test network disconnection (manual)
  # 1. Start a query
  # 2. Disconnect network
  # 3. Should see connection error with retry attempts

  # Clean up
  rm -f test_*.toml *_openai_*.md

  Expected Results:

  - Test 1: "Invalid OpenAI API key" with link to check API keys
  - Test 2: "openai API key not found" with suggestion to set OPENAI_API_KEY
  - Test 3: "Model 'gpt-5-does-not-exist' not found" with suggestion to check
  available models
  - Test 4: Should retry on timeout (see multiple attempts in verbose output)
  - Test 5: Response should be truncated at ~100 tokens
  - Test 6: "Failed to connect to OpenAI API" after retry attempts

  Error Messages Added:

  1. Invalid API Key: "Invalid OpenAI API key. Please check your API key at
  https://platform.openai.com/account/api-keys"
  2. Rate Limit: "Rate limit exceeded. Please wait a moment and try again."
  3. Model Not Found: "Model 'X' not found. Please check available models with 'thoth
   providers -- --models --provider openai'"
  4. Quota Exceeded: "API quota exceeded. Please check your OpenAI account billing."
  5. Connection Error: "Failed to connect to OpenAI API. Check your internet
  connection."
  6. Timeout: "Request timed out. Try increasing timeout in config."

  Once you've verified Phase 3 error handling works correctly, we can proceed to
  Phase 4 (Add M8T test cases).