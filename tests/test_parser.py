# tests/test_parser.py
import io
from unscheduler.parser import _parse_content

def test_simple_block_parsing():
    """Tests if the parser can handle a basic block event with an inline tag."""
    schedule_content = "Weekly M 9a 10a Test Event @TestCategory"
    
    # Use an in-memory text buffer to simulate a file
    mock_file_stream = io.StringIO(schedule_content)
    
    commitments, categories, non_work, errors = _parse_content(mock_file_stream)
    
    # --- Assertions: Check if the parser worked as expected ---
    assert not errors
    assert len(commitments) == 1
    assert len(categories) == 1
    assert "TestCategory" in categories
    
    event = commitments[0]
    assert event['recurrence'] == 'Weekly'
    assert event['day_code'] == 'M'
    assert event['type'] == 'block'
    assert event['start'] == '09:00'
    assert event['end'] == '10:00'
    assert event['event'] == 'Test Event'
    assert event['category'] == 'TestCategory'
    assert not event['spans_midnight']

def test_non_work_definition_parsing():
    """Tests if the parser correctly identifies non-work categories."""
    schedule_content = """
    [NON-WORK-DEFINITION]
    non_work_categories = Sleep, Family
    
    @Teaching
    Weekly F 1p 2p A real event
    """
    mock_file_stream = io.StringIO(schedule_content)
    
    _, _, non_work_cats, errors = _parse_content(mock_file_stream)
    
    assert not errors
    assert len(non_work_cats) == 2
    assert "Sleep" in non_work_cats
    assert "Family" in non_work_cats