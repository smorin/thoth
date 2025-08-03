# Missing Features Analysis: Implementation Plan v4.0 vs PRD v2.0

## Executive Summary

This document identifies features present in the implementation plan (thoth.plan.v4.md) that are not documented in the PRD v2.0 (thoth.v20.md), along with recommendations for inclusion.

---

## Missing Features from Implementation Plan

### 1. Graceful Shutdown (Ctrl-C) Handling
**Plan Reference**: M1-09, M1T-04
**Description**: Implement Ctrl-C graceful shutdown
**Status**: Not tested in plan
**PRD Status**: Referenced in N-03 but not as a functional requirement
**Recommendation**: Add as F-81 - "Implement graceful shutdown on Ctrl-C with checkpoint save"
**Priority**: High - Critical for user experience and data integrity

**Final Decision**: Add as F-81 - "Implement graceful shutdown on Ctrl-C with checkpoint save"

### 2. API Key Masking in Output
**Plan Reference**: M2-08, M2T-04
**Description**: Add API key validation and masking - "Errors appear in stdout not stderr"
**Status**: Not fully implemented
**PRD Status**: F-19 exists but implementation details missing
**Recommendation**: Clarify F-19 implementation requirements for masking in all outputs
**Priority**: High - Security requirement

**Final Decision**: Clarify F-19 implementation requirements for masking in all outputs based on M2-08 and M2T-04

### 3. Checkpoint Corruption Recovery
**Plan Reference**: M5-09, M5T-05
**Description**: Add checkpoint corruption recovery
**Status**: Basic structure exists
**PRD Status**: Mentioned in security section but not as functional requirement
**Recommendation**: Add as F-82 - "Implement checkpoint corruption detection and recovery"
**Priority**: Medium - Data integrity feature

**Final Decision**: Add as F-82 - "Implement checkpoint corruption detection and recovery"

### 4. Operation Lifecycle Management Details
**Plan Reference**: M5-10
**Description**: Create operation lifecycle management
**Status**: Not implemented
**PRD Status**: F-67 exists but lacks implementation details
**Recommendation**: Expand F-67 with specific lifecycle states and transitions
**Priority**: Medium - Operational requirement

**Final Decision**: Expand F-67 with specific lifecycle states and transitions


### 6. OpenAI Deep Research Features
**Plan Reference**: M8-01 through M10-08
**Description**: Comprehensive OpenAI provider implementation including:
- Streaming response support
- Token counting
- Cost estimation
- Model selection from config
- Temperature control
- Response caching
- Partial response saving on failure
**PRD Status**: Some features in F-54 through F-59 but not comprehensive
**Recommendation**: Add detailed OpenAI provider requirements section
**Priority**: High - Core functionality

**Final Decision**: Add detailed OpenAI provider requirements section for PRD

### 7. Perplexity-Specific Features
**Plan Reference**: M11-01 through M13-08
**Description**: Perplexity provider features:
- Citation extraction and formatting
- Web search mode
- Academic search mode
- Real-time data queries
- Search depth control
- Source filtering
- Source reliability scores
**PRD Status**: Basic provider support but missing Perplexity-specific features
**Recommendation**: Add F-83 through F-90 for Perplexity-specific capabilities
**Priority**: High - Provider parity

**Final Decision**: Add F-83 through F-90 for Perplexity-specific capabilities

### 8. Advanced Multi-Provider Features
**Plan Reference**: M14-01 through M14-07
**Description**: Advanced coordination features:
- Load balancing
- Circuit breaker pattern
- Dynamic provider selection
- Partial result handling
- Provider capability matching
- Performance monitoring
**PRD Status**: F-60 through F-65 cover basics but miss advanced patterns
**Recommendation**: Expand multi-provider section with advanced patterns
**Priority**: Medium - Advanced functionality

**Final Decision**: Expand multi-provider section with advanced patterns 


### 11. Test Infrastructure Features
**Plan Reference**: M22-01 through M22-05
**Description**: Test infrastructure for update/clean commands:
- Test fixtures for checkpoints
- Aged checkpoint generation
- Test cleanup utilities
**PRD Status**: Not documented
**Recommendation**: Add to testing requirements section
**Priority**: Medium - Testing infrastructure

**Final Decision**: Add to testing requirements section

### 12. Missing Core Features from Plan
**Plan Reference**: Section "Missing Core Features"
**Description**: Features referenced but not implemented:
- Watch Mode (--watch for live updates)
- Batch Mode (--batch for multiple queries)
- Template Mode (--template for repeated queries)
**PRD Status**: Not included
**Recommendation**: Consider for v2.1 or document as out of scope
**Priority**: Low - Advanced features


**Final Decision**: Remove the following features from the plan - 
- Watch Mode (--watch for live updates)
- Batch Mode (--batch for multiple queries)
- Template Mode (--template for repeated queries)
