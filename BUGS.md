# Known Bugs and Issues in Thoth

This document catalogues all known bugs, issues, and potential problems identified in the Thoth codebase as of the analysis date.

**Analysis Date:** December 28, 2024  
**Thoth Version:** 2.5.0  
**Reviewer:** Automated Code Analysis

## 🚨 Critical Bugs

### 1. **Event Loop Resource Leak in Signal Handler**
- **File:** `thoth:4189-4203`
- **Issue:** The signal handler creates a new event loop without properly cleaning it up
- **Code:**
  ```python
  def handle_sigint(signum, frame):
      # ...
      loop = asyncio.new_event_loop()
      asyncio.set_event_loop(loop)
      loop.run_until_complete(_current_checkpoint_manager.save(_current_operation))
      # Missing: loop.close()
  ```
- **Impact:** Memory leak when Ctrl-C is used repeatedly
- **Fix:** Add `loop.close()` in the finally block

### 2. **Global State Race Condition**
- **File:** `thoth:88-89, 2573-2574, 2793-2794`
- **Issue:** Global variables `_current_checkpoint_manager` and `_current_operation` can have race conditions in concurrent scenarios
- **Code:**
  ```python
  # Global variables for signal handling
  _current_checkpoint_manager = None
  _current_operation = None
  ```
- **Impact:** Potential data corruption if multiple operations run simultaneously
- **Fix:** Use thread-local storage or context variables instead of globals

### 3. **Incomplete JSON Error Handling**
- **File:** `thoth:1411-1414`
- **Issue:** JSON decoding errors are caught but checkpoint file corruption is only warned about, not handled
- **Code:**
  ```python
  except (json.JSONDecodeError, KeyError, ValueError):
      console.print(f"[yellow]Warning:[/yellow] Checkpoint file corrupted: {checkpoint_file}")
      return None  # Operation continues with None
  ```
- **Impact:** Silent failures and unpredictable behavior when checkpoint files are corrupted
- **Fix:** Implement proper recovery mechanism or fail gracefully with clear error messages

## ⚠️ High Priority Issues

### 4. **File Resource Leak in Output Manager**
- **File:** `thoth:2755-2756`
- **Issue:** File is opened without context manager (using `with`)
- **Code:**
  ```python
  with open(path, "r") as f:
      contents[provider_name] = f.read()
  ```
- **Impact:** This one is actually correct, but pattern should be consistent
- **Status:** False alarm - this is properly handled

### 5. **Debug Response Structure Exposure**
- **File:** `thoth:2104-2111`
- **Issue:** Debug code can potentially expose sensitive information in response structures
- **Code:**
  ```python
  # Debug: log response structure for troubleshooting
  try:
      if hasattr(response, "model_dump_json"):
          content = f"[Debug] Response structure: {response.model_dump_json()}"
  ```
- **Impact:** Could leak API keys or sensitive data in debug output
- **Fix:** Sanitize debug output to mask sensitive fields

### 6. **Hardcoded Timeout Values**
- **File:** `thoth_test:51, 421, 433, 482`
- **Issue:** Multiple hardcoded timeout values without configuration
- **Impact:** Tests may be flaky on slower systems
- **Fix:** Make timeouts configurable based on system performance

### 7. **Potential Deadlock in Interactive Mode**
- **File:** `thoth:4049-4057`
- **Issue:** Event loop detection and handling could cause deadlocks
- **Code:**
  ```python
  try:
      asyncio.get_running_loop()
      raise RuntimeError("Cannot use run() in async context, use run_async() instead")
  except RuntimeError:
      return asyncio.run(self.run_async())
  ```
- **Impact:** Could hang in certain async contexts
- **Fix:** Better async context detection and handling

## 🔍 Medium Priority Issues

### 8. **Inconsistent Error Exit Codes**
- **File:** `thoth:617` vs test expectations
- **Issue:** Code uses exit code 127 for unexpected errors, but tests expect different codes
- **Impact:** Inconsistent error reporting
- **Fix:** Standardize exit codes across codebase

### 9. **Cache Age Calculation Edge Case**
- **File:** `thoth:1629`
- **Issue:** Cache age calculated in days might not handle timezone edge cases properly
- **Code:**
  ```python
  return age.days < self.cache_max_age_days
  ```
- **Impact:** Cache might expire prematurely or stay too long
- **Fix:** Use more precise time calculations

### 10. **Missing Exception Handling in Provider Creation**
- **File:** `thoth:2601-2623`
- **Issue:** Provider creation has good error handling, but could be more granular
- **Impact:** Some provider errors might not have specific user-friendly messages
- **Fix:** Add more specific exception types

### 11. **Keyboard Binding Registration Errors**
- **File:** `thoth:3692-3711`
- **Issue:** Keyboard binding failures are silently ignored
- **Code:**
  ```python
  try:
      @kb.add("backtab")
      def handle_shift_tab_alt(event):
          handle_shift_tab(event)
  except Exception:
      # Some terminals may not support backtab
      pass
  ```
- **Impact:** Users might not have expected keyboard shortcuts
- **Fix:** Log which bindings failed for debugging

### 12. **Potential Memory Leak in Progress Tracking**
- **File:** `thoth:2696-2741`
- **Issue:** Long-running operations with frequent status checks might accumulate memory
- **Impact:** Memory usage growth over time
- **Fix:** Implement cleanup for old progress tracking data

## 🔧 Low Priority Issues

### 13. **TODO Comments Indicate Incomplete Features**
- **Files:** Multiple locations
- **TODOs Found:**
  - `thoth:1077` - Interactive setup wizard not implemented
  - `thoth:2229` - Perplexity submission not implemented
  - `thoth:2650` - Async task submission placeholder
  - `thoth:2815` - Resumption logic incomplete
  - `thoth:3372` - Status checking incomplete

### 14. **Inconsistent Code Style**
- **Issue:** Mixed use of string formatting methods (f-strings vs .format())
- **Impact:** Reduced code maintainability
- **Fix:** Standardize on f-strings throughout codebase

### 15. **Test Suite Timing Dependencies**
- **File:** `thoth_test:476`
- **Issue:** `time.sleep(0.1)` used for test synchronization
- **Impact:** Tests might be flaky under high load
- **Fix:** Use proper synchronization primitives

### 16. **Large Function Complexity**
- **Issue:** Several functions are too large and handle multiple responsibilities
- **Impact:** Reduced maintainability and testing difficulty
- **Fix:** Refactor into smaller, single-purpose functions

## 🧪 Test-Related Issues

### 17. **Disabled Critical Tests**
- **File:** `thoth_test:1117`
- **Issue:** Graceful shutdown test is disabled (`skip=True`)
- **Impact:** Critical functionality not being tested
- **Fix:** Enable and fix the test

### 18. **Interactive Test Reliability**
- **File:** `thoth_test:420-424`
- **Issue:** Interactive tests have fallback logic that might mask real issues
- **Code:**
  ```python
  try:
      child.expect("Thoth Interactive Mode", timeout=5)
  except (pexpect.TIMEOUT, pexpect.EOF):
      # Some tests might not show this, continue anyway
      pass
  ```
- **Impact:** Tests might pass when they should fail
- **Fix:** Make test expectations more precise

### 19. **Test Cleanup Incompleteness**
- **Issue:** Some test files are not cleaned up after test runs
- **Impact:** Disk space usage and potential test interference
- **Fix:** Ensure comprehensive cleanup in all test cases

## 🔐 Security Concerns

### 20. **API Key Exposure in Debug Mode**
- **Issue:** Debug output might contain API keys despite masking attempts
- **Impact:** Potential credential exposure
- **Fix:** Implement stronger sanitization for all debug outputs

### 21. **Configuration File Security**
- **Issue:** Config files with API keys might have incorrect permissions
- **Impact:** Potential credential exposure to other users
- **Fix:** Set restrictive permissions on config files

## 📊 Analysis Summary

| Category | Count | Severity |
|----------|-------|----------|
| Critical Bugs | 3 | 🚨 |
| High Priority | 5 | ⚠️ |
| Medium Priority | 6 | 🔍 |
| Low Priority | 4 | 🔧 |
| Test Issues | 3 | 🧪 |
| Security | 2 | 🔐 |
| **Total** | **23** | |

## 🛠️ Recommended Action Plan

### Immediate (Critical - Fix First)
1. Fix event loop leak in signal handler
2. Replace global variables with thread-safe alternatives
3. Implement proper checkpoint corruption handling

### Short Term (High Priority)
4. Sanitize debug output for security
5. Make test timeouts configurable
6. Fix potential deadlock in interactive mode

### Medium Term (Medium Priority)
7. Standardize error exit codes
8. Improve cache age calculations
9. Enhance provider error handling

### Long Term (Low Priority)
10. Implement all TODO items
11. Refactor large functions
12. Standardize code style

## 🔍 Analysis Methodology

This analysis was conducted using:
- Static code analysis with `grep` patterns
- Manual code review of key sections
- Pattern matching for common bug types:
  - Resource leaks
  - Race conditions
  - Error handling gaps
  - Event loop issues
  - File operations
  - Global state problems
  - Test reliability issues

## 📝 Notes

- The codebase generally shows good practices with async/await patterns
- Error handling is comprehensive in most areas
- Test coverage appears extensive but some critical tests are disabled
- The modular structure makes most bugs isolated to specific components

---

*This document should be updated as bugs are fixed and new issues are discovered.*