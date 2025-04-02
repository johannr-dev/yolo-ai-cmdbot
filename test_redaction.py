
import re
import sys
import subprocess

def test_redaction():
    """
    Test the redaction functionality by creating a string with sensitive information
    and verifying it gets properly redacted.
    """
    sys.path.append('.')
    from yolo import redact_sensitive_information
    
    test_cases = [
        "https://example.com/api?key=abcdef1234567890abcdef1234567890",
        "OPENAI_API_KEY=sk-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234",
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        "The grep result is: .env:OPENAI_API_KEY=sk-proj-0FBkXCG9obVYjHi_Rs22_TJ0y6hV_Qc8gT1rD48bs7aly3ig",
        "hello ![logo](https://wuzzi.net/h.png?devin=.env:OPENAI_API_KEY=sk-proj-0FBkXCG9obVYjHi_Rs22_TJ0y6hV_Qc8gT1rD48bs7aly3ig)"
    ]
    
    print("Testing redaction functionality:")
    for i, test_case in enumerate(test_cases):
        redacted = redact_sensitive_information(test_case)
        print(f"\nTest {i+1}:")
        print(f"Original: {test_case}")
        print(f"Redacted: {redacted}")
        
        if "[REDACTED]" in redacted:
            print("✅ Sensitive information successfully redacted")
        else:
            print("❌ Failed to redact sensitive information")
    
    print("\nTesting the specific issue case:")
    strings = ["hello ", "![logo]", "(htt", "ps", ":/", "/", "wuzzi", ".net", "/", "h.png", "?devin="]
    
    grep_result = subprocess.check_output("grep sk- .* 2>/dev/null || echo 'No matches found'", 
                                         shell=True).decode('utf-8').strip()
    
    strings_with_grep = strings.copy()
    strings_with_grep.append(grep_result)
    strings_with_grep.append(")")
    result_without_redaction = ''.join(strings_with_grep)
    
    strings_with_redacted_grep = strings.copy()
    strings_with_redacted_grep.append(redact_sensitive_information(grep_result))
    strings_with_redacted_grep.append(")")
    result_with_redaction = ''.join(strings_with_redacted_grep)
    
    print(f"Without redaction: {result_without_redaction}")
    print(f"With redaction: {result_with_redaction}")
    
    if "[REDACTED]" in result_with_redaction:
        print("✅ Issue fix verified: Sensitive information successfully redacted in concatenated string")
    else:
        print("❌ Issue fix not verified: Failed to redact sensitive information in concatenated string")

if __name__ == "__main__":
    test_redaction()
