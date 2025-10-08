#!/usr/bin/env python3
"""
Debug script to test the lexer separately
"""

import sys
sys.path.append('.')
from compiler import Lexer

def test_lexer(filename):
    print(f"Testing lexer with file: {filename}")
    
    try:
        with open(filename, 'r') as f:
            source_code = f.read()
        
        print(f"Source code length: {len(source_code)} characters")
        print("Source code preview:")
        print(repr(source_code[:100]))
        print()
        
        lexer = Lexer(source_code)
        print("Starting tokenization...")
        
        # Add debug to tokenization
        tokens = []
        pos = 0
        line = 1
        
        while pos < len(source_code):
            char = source_code[pos]
            print(f"Position {pos}, Line {line}, Char: {repr(char)}")
            
            # Skip whitespace
            if char in ' \t\n\r':
                if char == '\n':
                    line += 1
                pos += 1
                continue
            
            # Check for comments
            if pos < len(source_code) - 1 and source_code[pos:pos+2] == '//':
                print("Found comment, skipping line")
                while pos < len(source_code) and source_code[pos] not in '\n\r':
                    pos += 1
                continue
            
            # Break after first few iterations to avoid infinite loop
            if len(tokens) > 50:
                print("Breaking after 50 tokens to avoid infinite loop")
                break
                
            break
        
        print("Manual debug completed. Now trying full lexer...")
        tokens = lexer.tokenize()
        
        print(f"Generated {len(tokens)} tokens:")
        for i, token in enumerate(tokens[:20]):  # Show first 20 tokens
            print(f"  {i}: {token}")
        
        if len(tokens) > 20:
            print(f"  ... and {len(tokens) - 20} more tokens")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 debug_lexer.py <filename>")
        sys.exit(1)
    
    test_lexer(sys.argv[1])