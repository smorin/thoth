# Thoth v12 - Remaining Questions and Minor Clarifications

## Summary

After applying all recommendations from temp.v4.md to create thoth.v12.md, the PRD is now comprehensive and production-ready. Most outstanding questions have been addressed. Only a few minor clarifications remain that could be considered during implementation.

---

## 1. Progress Reporting Granularity

### Current State
F-38 specifies progress percentages are "estimated based on typical operation times", and the implementation shows hardcoded estimates for each mode/provider combination.

### Remaining Question
- Should the progress estimates be configurable in the config file for users who consistently see different timing patterns?
- Could providers report actual progress if their APIs support it in the future?

### Recommendation
The current approach is sufficient for v1.2. Consider adding configurable estimates in a future version if users report significant variance.

---

## 2. Combined Report Conflict Resolution

### Current State
The combined report simply concatenates results from different providers with section headers.

### Remaining Question
- Should there be any attempt to identify and highlight conflicting information between providers?
- Should the combined report include a summary section?

### Recommendation
The simple concatenation approach is appropriate for v1.2. More sophisticated synthesis could be added in future versions.

---

## 3. Auto-input Time Window

### Current State
Auto-input finds the latest files from the previous mode without any time constraints.

### Remaining Question
- Should there be a configurable time window (e.g., only use outputs from the last 24 hours)?
- This could prevent accidentally using very old outputs.

### Recommendation
Not critical for v1.2. Could add an optional `auto_input_max_age` config setting in the future.

---

## 4. Provider Failover Strategy

### Current State
When a provider fails, the system continues with other providers and notes the failure.

### Remaining Question
- Should there be an option to automatically retry with a different model (e.g., fallback from o1-deep-research to gpt-4)?
- Should certain errors trigger different behaviors (quota vs network vs invalid request)?

### Recommendation
Current behavior is appropriate. The retry logic with exponential backoff handles transient failures well.

---

## 5. Operation Cleanup Policy

### Current State
The PRD doesn't specify when old operations are removed from the checkpoint directory.

### Remaining Question
- Should there be automatic cleanup of completed operations older than N days?
- Should `thoth list` have a `--clean` option to remove old operations?

### Recommendation
Not critical for v1.2. Manual cleanup is sufficient initially. Could add retention policies in v1.3.

---

## Implementation Ready

The PRD is now complete and ready for implementation. All major design decisions have been made:

✓ Clear provider selection behavior
✓ Well-defined file matching patterns
✓ Comprehensive error handling
✓ Configuration versioning system
✓ Detailed progress tracking approach
✓ Complete CLI interface specification
✓ Robust checkpoint/resume functionality

The remaining questions above are minor optimizations that can be addressed in future versions based on user feedback. The current specification provides a solid foundation for a production-quality tool.

## Development Priorities

1. **Core Functionality** - Focus on the multi-provider orchestration and async handling
2. **Error Handling** - Implement all specified error cases with clear messages
3. **Progress Tracking** - Use the estimated times approach as specified
4. **Combined Reports** - Simple concatenation as designed
5. **Testing** - Ensure checkpoint recovery and mode chaining work reliably

No blocking issues remain. The specification is ready for implementation.