"""
Unit tests for markdown_parser module.
"""

import pytest
from maestro.data.markdown_parser import (
    parse_quoted_value,
    parse_status_badge,
    parse_completion,
    parse_checkbox,
    parse_heading,
    parse_track_heading,
    parse_phase_heading,
    parse_task_heading,
    parse_metadata_block,
    parse_track,
    parse_phase,
    parse_task,
)


class TestParseQuotedValue:
    """Tests for parse_quoted_value function."""

    def test_parse_string_value(self):
        result = parse_quoted_value('"name": "Test Track"')
        assert result == ('name', 'Test Track')

    def test_parse_integer_value(self):
        result = parse_quoted_value('"priority": 1')
        assert result == ('priority', 1)

    def test_parse_float_value(self):
        result = parse_quoted_value('"completion": 45.5')
        assert result == ('completion', 45.5)

    def test_parse_boolean_true(self):
        result = parse_quoted_value('"enabled": true')
        assert result == ('enabled', True)

    def test_parse_boolean_false(self):
        result = parse_quoted_value('"enabled": false')
        assert result == ('enabled', False)

    def test_parse_null_value(self):
        result = parse_quoted_value('"current_track": null')
        assert result == ('current_track', None)

    def test_parse_with_extra_whitespace(self):
        result = parse_quoted_value('  "name"  :   "Value"  ')
        assert result == ('name', 'Value')

    def test_parse_invalid_format(self):
        result = parse_quoted_value('name: "value"')  # Missing quotes on key
        assert result is None

    def test_parse_empty_string(self):
        result = parse_quoted_value('"name": ""')
        assert result == ('name', '')


class TestParseStatusBadge:
    """Tests for parse_status_badge function."""

    def test_parse_done_status(self):
        result = parse_status_badge('✅ **Done**')
        assert result == 'done'

    def test_parse_in_progress_status(self):
        result = parse_status_badge('🚧 **In Progress**')
        assert result == 'in_progress'

    def test_parse_planned_status(self):
        result = parse_status_badge('📋 **Planned**')
        assert result == 'planned'

    def test_parse_proposed_status(self):
        result = parse_status_badge('💡 **Proposed**')
        assert result == 'proposed'

    def test_parse_with_brackets(self):
        result = parse_status_badge('🚧 **[In Progress]**')
        assert result == 'in_progress'

    def test_parse_in_context(self):
        result = parse_status_badge('- [ ] [Phase umk1: Core](phases/umk1.md) 📋 **[Planned]**')
        assert result == 'planned'

    def test_parse_no_match(self):
        result = parse_status_badge('No status here')
        assert result is None


class TestParseCompletion:
    """Tests for parse_completion function."""

    def test_parse_simple_percentage(self):
        result = parse_completion('**45%**')
        assert result == 45

    def test_parse_completion_label(self):
        result = parse_completion('**Completion**: 67%')
        assert result == 67

    def test_parse_in_context(self):
        result = parse_completion('Status: 🚧 **In Progress** **50%**')
        assert result == 50

    def test_parse_no_match(self):
        result = parse_completion('No percentage here')
        assert result is None


class TestParseCheckbox:
    """Tests for parse_checkbox function."""

    def test_parse_unchecked_checkbox(self):
        result = parse_checkbox('- [ ] Task 1')
        assert result == (0, False, 'Task 1')

    def test_parse_checked_checkbox(self):
        result = parse_checkbox('- [x] Task 1')
        assert result == (0, True, 'Task 1')

    def test_parse_indented_checkbox(self):
        result = parse_checkbox('  - [ ] Subtask 1.1')
        assert result == (2, False, 'Subtask 1.1')

    def test_parse_deeply_indented(self):
        result = parse_checkbox('    - [x] Deep subtask')
        assert result == (4, True, 'Deep subtask')

    def test_parse_complex_content(self):
        result = parse_checkbox('- [ ] **Task 1.1: Parser Module**')
        assert result == (0, False, '**Task 1.1: Parser Module**')

    def test_parse_no_match(self):
        result = parse_checkbox('Not a checkbox')
        assert result is None


class TestParseHeading:
    """Tests for parse_heading function."""

    def test_parse_h1(self):
        result = parse_heading('# Heading 1')
        assert result == (1, 'Heading 1')

    def test_parse_h2(self):
        result = parse_heading('## Heading 2')
        assert result == (2, 'Heading 2')

    def test_parse_h3(self):
        result = parse_heading('### Heading 3')
        assert result == (3, 'Heading 3')

    def test_parse_h6(self):
        result = parse_heading('###### Heading 6')
        assert result == (6, 'Heading 6')

    def test_parse_with_extra_spaces(self):
        result = parse_heading('##  Spaced  Heading  ')
        assert result == (2, 'Spaced  Heading')

    def test_parse_no_match(self):
        result = parse_heading('Not a heading')
        assert result is None


class TestParseTrackHeading:
    """Tests for parse_track_heading function."""

    def test_parse_simple_track(self):
        result = parse_track_heading('## Track: UMK Integration')
        assert result == 'UMK Integration'

    def test_parse_top_priority_track(self):
        result = parse_track_heading('## 🔥 TOP PRIORITY Track: CLI System')
        assert result == 'CLI System'

    def test_parse_with_status(self):
        result = parse_track_heading('## Track: Build System 🚧 **[In Progress]**')
        assert result == 'Build System'

    def test_parse_no_match(self):
        result = parse_track_heading('## Not a Track')
        assert result is None


class TestParsePhaseHeading:
    """Tests for parse_phase_heading function."""

    def test_parse_numeric_phase(self):
        result = parse_phase_heading('### Phase umk1: Core Builder Abstraction')
        assert result == ('umk1', 'Core Builder Abstraction')

    def test_parse_alphanumeric_phase(self):
        result = parse_phase_heading('### Phase CLI1: Markdown Data Backend')
        assert result == ('CLI1', 'Markdown Data Backend')

    def test_parse_with_status(self):
        result = parse_phase_heading('### Phase TU2: Incremental Builder 📋 **[Planned]**')
        assert result == ('TU2', 'Incremental Builder')

    def test_parse_no_match(self):
        result = parse_phase_heading('### Not a Phase')
        assert result is None


class TestParseTaskHeading:
    """Tests for parse_task_heading function."""

    def test_parse_simple_task(self):
        result = parse_task_heading('**Task 1.1: Parser Module**')
        assert result == ('1.1', 'Parser Module')

    def test_parse_task_in_checkbox(self):
        result = parse_task_heading('- [ ] **Task 1.2: Writer Module**')
        assert result == ('1.2', 'Writer Module')

    def test_parse_checked_task(self):
        result = parse_task_heading('- [x] **Task 1.3: Testing**')
        assert result == ('1.3', 'Testing')

    def test_parse_complex_number(self):
        result = parse_task_heading('**Task 12.5.3: Subtask**')
        assert result == ('12.5.3', 'Subtask')

    def test_parse_no_match(self):
        result = parse_task_heading('Not a task')
        assert result is None


class TestParseMetadataBlock:
    """Tests for parse_metadata_block function."""

    def test_parse_simple_metadata(self):
        lines = [
            '"name": "Test Track"',
            '"priority": 1',
            '"status": "planned"',
        ]
        metadata, idx = parse_metadata_block(lines)
        assert metadata == {
            'name': 'Test Track',
            'priority': 1,
            'status': 'planned',
        }
        assert idx == 3

    def test_parse_with_empty_lines(self):
        lines = [
            '',
            '"name": "Test"',
            '"priority": 1',
            '',
            'Next section',
        ]
        metadata, idx = parse_metadata_block(lines)
        assert metadata == {'name': 'Test', 'priority': 1}
        assert idx == 4

    def test_parse_stops_at_non_metadata(self):
        lines = [
            '"name": "Test"',
            'Regular text',
            '"priority": 1',
        ]
        metadata, idx = parse_metadata_block(lines)
        assert metadata == {'name': 'Test'}
        assert idx == 1


class TestParseTrack:
    """Tests for parse_track function."""

    def test_parse_simple_track(self):
        lines = [
            '## Track: Test Track',
            '',
            '"track_id": "test-1"',
            '"priority": 1',
            '',
            'This is the track description.',
        ]
        track, idx = parse_track(lines, 0)
        assert track['name'] == 'Test Track'
        assert track['track_id'] == 'test-1'
        assert track['priority'] == 1
        assert 'This is the track description.' in track['description']


class TestParsePhase:
    """Tests for parse_phase function."""

    def test_parse_simple_phase(self):
        lines = [
            '### Phase 1: Test Phase',
            '',
            '"phase_id": "test-1"',
            '"status": "planned"',
            '',
            'Phase description here.',
        ]
        phase, idx = parse_phase(lines, 0)
        # Metadata overrides the parsed phase_id from heading
        assert phase['phase_id'] == 'test-1'
        assert phase['name'] == 'Test Phase'
        assert phase['status'] == 'planned'


class TestParseTask:
    """Tests for parse_task function."""

    def test_parse_simple_task(self):
        lines = [
            '- [ ] **Task 1.1: Test Task**',
            '"task_id": "test-1-1"',
            '"priority": "P0"',
            '',
            'Task description.',
        ]
        task, idx = parse_task(lines, 0)
        assert task['task_number'] == '1.1'
        assert task['name'] == 'Test Task'
        assert task['task_id'] == 'test-1-1'
        assert task['priority'] == 'P0'
        assert task['completed'] is False

    def test_parse_completed_task(self):
        lines = [
            '- [x] **Task 1.2: Completed Task**',
        ]
        task, idx = parse_task(lines, 0)
        assert task['completed'] is True

    def test_parse_task_with_subtasks(self):
        lines = [
            '- [ ] **Task 1.1: Main Task**',
            '',
            '- [ ] Subtask 1',
            '- [x] Subtask 2',
            '  - [ ] Deep subtask',
        ]
        task, idx = parse_task(lines, 0)
        assert len(task['subtasks']) == 3
        assert task['subtasks'][0]['content'] == 'Subtask 1'
        assert task['subtasks'][0]['completed'] is False
        assert task['subtasks'][0]['indent'] == 0
        assert task['subtasks'][1]['completed'] is True
        assert task['subtasks'][1]['indent'] == 0
        # Deep subtask has 2-space indent
        assert task['subtasks'][2]['content'] == 'Deep subtask'
        assert task['subtasks'][2]['indent'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
