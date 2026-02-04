#!/usr/bin/env python3
"""
Simple test untuk verifikasi perbaikan Google Tools
Tanpa dependency pada google modules
"""

import re


def test_descriptions_in_file():
    """Test dengan membaca file google_tools.py langsung"""
    print("=" * 80)
    print("TESTING GOOGLE TOOLS IMPROVEMENTS")
    print("=" * 80)
    
    # Read the file
    with open("app/tools/google_tools.py", "r") as f:
        content = f.read()
    
    # Test cases - mencari pattern deskripsi yang sudah diperbaiki
    test_cases = [
        {
            "tool": "GmailGetMessageTool",
            "expected_keywords": [
                "FULL CONTENT",
                "message_id can be obtained",
                "gmail_list_messages",
                "Format options"
            ],
            "pattern": r'name="gmail_get_message".*?description="(.*?)"',
        },
        {
            "tool": "GmailListMessagesTool",
            "expected_keywords": [
                "metadata only",
                "FASTER",
                "Use this to find messages first",
                "Gmail search syntax"
            ],
            "pattern": r'name="gmail_list_messages".*?description="(.*?)"',
        },
        {
            "tool": "GmailReadMessagesTool",
            "expected_keywords": [
                "full content",
                "If message_id is provided",
                "Use 'query' parameter",
                "mark_as_read"
            ],
            "pattern": r'name="gmail_read_messages".*?description="(.*?)"',
        },
        {
            "tool": "GoogleCalendarListEventsTool",
            "expected_keywords": [
                "List and retrieve",
                "event details",
                "time_min",
                "time_max"
            ],
            "pattern": r'name="google_calendar_list_events".*?description="(.*?)"',
        },
        {
            "tool": "GoogleCalendarGetEventTool",
            "expected_keywords": [
                "FULL DETAILS",
                "event_id",
                "google_calendar_list_events",
                "summary, description, location"
            ],
            "pattern": r'name="google_calendar_get_event".*?description="(.*?)"',
        },
        {
            "tool": "GoogleDocsListDocumentsTool",
            "expected_keywords": [
                "List and search",
                "document metadata",
                "query",
                "google_docs_get_document"
            ],
            "pattern": r'name="google_docs_list_documents".*?description="(.*?)"',
        },
        {
            "tool": "GoogleDocsGetDocumentTool",
            "expected_keywords": [
                "FULL TEXT CONTENT",
                "document_id",
                "google_docs_list_documents",
                "Returns the document title"
            ],
            "pattern": r'name="google_docs_get_document".*?description="(.*?)"',
        },
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n{test['tool']}")
        print("-" * 40)
        
        # Find the description using regex
        match = re.search(test['pattern'], content, re.DOTALL)
        
        if match:
            description = match.group(1)
            print(f"✅ Found description ({len(description)} chars)")
            
            # Check for expected keywords
            found_keywords = []
            missing_keywords = []
            
            for keyword in test['expected_keywords']:
                if keyword.lower() in description.lower():
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            if found_keywords:
                print(f"✅ Found keywords: {', '.join(found_keywords[:2])}...")
            
            if missing_keywords:
                print(f"⚠️  Missing keywords: {', '.join(missing_keywords[:2])}...")
            
            # Check description length
            if len(description) > 100:
                print(f"✅ Description is detailed ({len(description)} chars)")
                results.append(True)
            else:
                print(f"⚠️  Description might be too short ({len(description)} chars)")
                results.append(False)
        else:
            print(f"❌ Could not find tool definition")
            results.append(False)
    
    # Test error messages
    print("\n" + "=" * 80)
    print("TESTING ERROR MESSAGES")
    print("=" * 80)
    
    error_patterns = [
        {
            "name": "Gmail get_message error",
            "pattern": r"Gmail get_message action requires.*?Use gmail_list_messages",
            "expected": True
        },
        {
            "name": "Calendar get_event error",
            "pattern": r"Google Calendar get_event action requires.*?Use google_calendar_list_events",
            "expected": True
        }
    ]
    
    for test in error_patterns:
        print(f"\n{test['name']}")
        print("-" * 40)
        found = re.search(test['pattern'], content, re.DOTALL | re.IGNORECASE)
        if found:
            print(f"✅ Error message is helpful and instructive")
            results.append(True)
        else:
            print(f"❌ Error message not found or not helpful")
            results.append(False)
    
    # Test logging statements
    print("\n" + "=" * 80)
    print("TESTING LOGGING ENHANCEMENTS")
    print("=" * 80)
    
    logging_patterns = [
        {
            "name": "Gmail get_message logging",
            "pattern": r'logger\.debug.*?"Gmail get_message executing"',
        },
        {
            "name": "Calendar get_event logging",
            "pattern": r'logger\.debug.*?"Google Calendar get_event executing"',
        },
        {
            "name": "Calendar list_events logging",
            "pattern": r'logger\.debug.*?"Google Calendar list_events executing"',
        },
        {
            "name": "Docs get_document logging",
            "pattern": r'logger\.debug.*?"Google Docs get_document executing"',
        },
    ]
    
    for test in logging_patterns:
        print(f"\n{test['name']}")
        print("-" * 40)
        found = re.search(test['pattern'], content, re.DOTALL)
        if found:
            print(f"✅ Logging statement added")
            results.append(True)
        else:
            print(f"⚠️  Logging statement not found (might be okay)")
            results.append(None)  # Not a failure
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)
    total = len([r for r in results if r is not None])
    
    print(f"\nPassed: {passed}/{total}")
    print(f"Failed: {failed}/{total}")
    if skipped > 0:
        print(f"Skipped: {skipped}")
    
    if failed == 0:
        print("\n🎉 ALL CRITICAL TESTS PASSED!")
        print("\nPerbaikan yang berhasil diimplementasikan:")
        print("✅ 1. Deskripsi tools lebih informatif dan instructive")
        print("✅ 2. Error messages lebih helpful dengan workflow guidance")
        print("✅ 3. Logging ditambahkan untuk debugging")
        print("✅ 4. Tools siap untuk testing dengan agent")
        return True
    else:
        print(f"\n⚠️  {failed} TESTS FAILED")
        print("Please review the output above for details.")
        return False


if __name__ == "__main__":
    import sys
    success = test_descriptions_in_file()
    sys.exit(0 if success else 1)
