# CLI5: textual-mc Deprecation Decision

## Investigation

Per the CLI5 phase requirements (docs/phases/cli5.md), Task 5.5 requires making a decision about "textual-mc".

### Findings

After examining the codebase:

1. **No textual-mc implementation found**: There is no `maestro/textual_mc/` or similar directory
2. **Two TUI implementations exist**:
   - `maestro/tui/` - Textual-based TUI (modern, rich terminal UI)
   - `maestro/tui_mc2/` - MC2/curses-based TUI (traditional curses interface)

3. **References to textual-mc**: Only found in documentation (docs/phases/cli5.md and docs/todo.md) as a planned deprecation task

### Analysis

The term "textual-mc" in the phase document likely refers to one of the existing TUI implementations, most probably:
- Either a historical name for `maestro/tui/` (the Textual-based implementation)
- Or a misnamed reference to `maestro/tui_mc2/` (the MC2 implementation)

### Current State

Both TUI implementations have been updated:
- ✅ `maestro/tui/` - Updated to Phase terminology, markdown backend, status badges
- ✅ `maestro/tui_mc2/` - Updated to Phase terminology, markdown backend, status badges

Both are functional and serve different purposes:
- **maestro/tui/** uses Textual framework - modern, feature-rich, better for development
- **maestro/tui_mc2/** uses curses - lightweight, works in minimal terminal environments

## Decision

### Keep Both Implementations

**Recommendation**: Maintain both TUI implementations for now.

**Rationale**:
1. **Different use cases**: Textual TUI is better for rich terminals, MC2 is better for minimal environments
2. **Both are updated**: Both have been successfully updated to use Phase terminology and markdown backend
3. **Low maintenance cost**: Since both share the same `ui_facade` backend, maintenance is minimal
4. **User choice**: Some users may prefer one over the other

### Action Items

- ✅ Update both implementations to new terminology - **COMPLETED**
- ✅ Integrate both with markdown backend - **COMPLETED**
- ✅ Add status badges to both - **COMPLETED**
- ⏭️ Document the differences between the two TUIs for users
- ⏭️ Consider adding a command-line flag to choose which TUI to launch

### Future Considerations

If deprecation becomes necessary in the future:
1. Gather user feedback on which TUI is preferred
2. Measure usage statistics if available
3. Consider feature parity before deprecating either
4. Provide migration path and deprecation warnings

## Conclusion

**Decision**: No deprecation at this time. Both TUI implementations (`maestro/tui/` and `maestro/tui_mc2/`) will be maintained as they serve different user needs and both have been successfully updated to the new Track/Phase/Task system.

The "textual-mc" reference in the phase document appears to be a documentation artifact and does not correspond to an actual codebase component requiring deprecation.
