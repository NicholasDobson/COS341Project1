#!/usr/bin/env python3
"""
Debug lexer for infinite loop detection
"""

import sys
sys.path.append('.')

def debug_tokenize(filename):
    print(f"Debugging tokenization of {filename}")
    
    with open(filename, 'r') as f:
        text = f.read()
    
    print(f"File length: {len(text)} characters")
    print("First 200 characters:")
    print(repr(text[:200]))
    print()
    
    pos = 0
    line = 1
    token_count = 0
    
    while pos < len(text) and token_count < 100:  # Safety limit
        old_pos = pos
        char = text[pos] if pos < len(text) else 'EOF'
        print(f"Token {token_count}: pos={pos}, line={line}, char={repr(char)}")
        
        # Skip whitespace
        while pos < len(text) and text[pos] in ' \t\n\r':
            if text[pos] == '\n':
                line += 1
            pos += 1
        
        if pos >= len(text):
            break
            
        # Check comments
        if pos < len(text) - 1 and text[pos:pos+2] == '//':
            print(f"  -> Found comment at pos {pos}")
            while pos < len(text) and text[pos] not in '\n\r':
                pos += 1
            continue
        
        char = text[pos]
        
        # String
        if char == '"':
            print(f"  -> Found string starting at pos {pos}")
            start = pos
            pos += 1
            count = 0
            while pos < len(text) and text[pos] != '"' and count < 15:
                pos += 1
                count += 1
            if pos < len(text) and text[pos] == '"':
                pos += 1
            print(f"  -> String token: {repr(text[start:pos])}")
            token_count += 1
            continue
            
        # Number
        if char.isdigit():
            print(f"  -> Found number starting at pos {pos}")
            start = pos
            while pos < len(text) and text[pos].isdigit():
                pos += 1
            print(f"  -> Number token: {text[start:pos]}")
            token_count += 1
            continue
            
        # Identifier
        if char.islower():
            print(f"  -> Found identifier starting at pos {pos}")
            start = pos
            while pos < len(text) and text[pos].islower():
                pos += 1
            while pos < len(text) and text[pos].isdigit():
                pos += 1
            print(f"  -> Identifier token: {text[start:pos]}")
            token_count += 1
            continue
            
        # Symbol
        if char in '(){}[];=><':
            print(f"  -> Found symbol: {char}")
            pos += 1
            token_count += 1
            continue
            
        # Unknown
        print(f"  -> Unknown character: {repr(char)}, skipping")
        pos += 1
        
        # Safety check for infinite loop
        if pos == old_pos:
            print("ERROR: Position didn't advance! Breaking to prevent infinite loop.")
            break
            
    print(f"\nProcessed {token_count} tokens")
    print(f"Final position: {pos}/{len(text)}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 debug_tokenize.py <filename>")
        sys.exit(1)
    
    debug_tokenize(sys.argv[1])